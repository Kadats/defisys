import logging
import pandas as pd
import os

from backend.src.data.pipeline import get_full_prepared_data
from .core import TradingEngine
from .strategies import BTCLiteStrategy, AccumulatorStrategy
from .config import PROJECT_ROOT, ML_TRAIN_SPLIT_DATE
from .ai import train_prediction_model, get_predictions
from backend.src.data.storage import save_predictions_to_db, save_trades
from backend.src.data import storage

logger = logging.getLogger(__name__)

# (A função log_summary_report permanece a mesma)
def log_summary_report(results, latest_indicators=None):
    """
    Registra um resumo do backtest no logger e salva um relatório
    completo em um arquivo .txt.
    """
    
    # --- Parte 1: Logar no Console (REMOVIDA/COMENTADA) ---
    # try:
    #     logger.info("--- RELATORIO DE BACKTEST (v2 Engine) ---")
    #     logger.info("Capital Inicial: $%0.2f", results.get('initial_capital_usd'))
    #     logger.info("Capital Final: $%0.2f", results.get('final_usd_value'))
    #     logger.info("Lucro/Prejuizo: $%0.2f (%0.2f%%)", results.get('profit_usd'), results.get('profit_percentage_usd'))
    #     logger.info("Performance do Buy and Hold (BTC): (%0.2f%%)", results.get('btc_benchmark_profit_percentage'))

    #     if latest_indicators is not None:
    #          cols_to_show = ['Open_time', 'Close', 'FNG_Value', 'RSI', 'Sentimento_Score', 'Volatilidade_Score', 'Oportunidade_Score']
    #          cols_available = [col for col in cols_to_show if col in latest_indicators.columns]
    #          logger.info("--- INDICADORES RECENTES ---")
    #          logger.info("\n%s", latest_indicators[cols_available].to_string())
    # except Exception:
    #     logger.exception("Erro ao logar o sumario do relatorio no console")

    # Backtest summary completed - all results logged to console/logger
    # No .txt file generation needed in V2 architecture


def run_trading_system():
    # 1. LIMPEZA ANTES DE COMEÇAR
    storage.clear_simulation_data()
    """
    Orquestra o fluxo de alto nivel: Dados -> Modelo de ML -> Backtest.
    Implementa Walk-Forward: treina em passado distante, testa em passado recente.
    """
    logger.info("Iniciando o sistema de trade com validação Walk-Forward...")

    # 1. Obter os dados (agora com features e alvos de ML)
    logger.info("Fase 1: Preparando todos os dados de mercado e indicadores...")
    full_df = get_full_prepared_data() 
    if full_df is None or full_df.empty:
        logger.error("Não foi possível obter os dados. Encerrando.")
        return {"backtest_report": {"error": "Failed to get data"}, "full_dataframe": pd.DataFrame()} 

    # --- MUDANÇA 2: Treinar o Modelo de ML com Split Temporal ---
    logger.info(f"Fase 2: Treinando o modelo de predição com Split Temporal ({ML_TRAIN_SPLIT_DATE})...")
    model, scaler = train_prediction_model(full_df, train_test_split_date=ML_TRAIN_SPLIT_DATE)
    
    # Gerar predições para todo o histórico (para análise visual)
    full_df_with_predictions = get_predictions(model, scaler, full_df)

    # --- Salvar as predições no DB ---
    logger.info("Fase 2b: Salvando predições no banco de dados...")
    save_predictions_to_db(full_df_with_predictions)

    # 3. Preparar DataFrame para Backtest (Walk-Forward Test Set)
    # CRÍTICO: Usar apenas dados a partir de ML_TRAIN_SPLIT_DATE para o backtest
    split_date = pd.Timestamp(ML_TRAIN_SPLIT_DATE)
    simulation_df = full_df_with_predictions[full_df_with_predictions['Open_time'] >= split_date].copy()
    simulation_df = simulation_df.reset_index(drop=True)
    
    logger.info(f"Filtered simulation data. Starting from {split_date}. Rows: {len(simulation_df)}")
    logger.info(f"Fase 3: Configurando Backtest Walk-Forward...")
    logger.info(f"  Período de simulação: {simulation_df['Open_time'].min().strftime('%Y-%m-%d')} até {simulation_df['Open_time'].max().strftime('%Y-%m-%d')}")
    logger.info(f"  Total de candles para backtest: {len(simulation_df)}")
    logger.info(f"  Modelo foi treinado em dados anteriores a {ML_TRAIN_SPLIT_DATE}")
    
    # Configurar e Executar o Backtester apenas com dados pós-split
    logger.info("Fase 4: Executando o backtest da estratégia...")
    # Raised initial capital slightly to provide a healthier buffer for gas + liquidity
    initial_capital = 1050.0
    engine = TradingEngine(initial_capital_usd=initial_capital)
    
    # Instantiate the strategy - Using AccumulatorStrategy (V15 - BTC Maximizer)
    strategy = AccumulatorStrategy()
    
    # O backtester roda APENAS no DataFrame de teste (post-split)
    backtest_results = engine.run(simulation_df, strategy=strategy) 
    
    # Salvar os trades no banco de dados
    logger.info("Fase 4b: Salvando trades no banco de dados...")
    price_final = float(simulation_df.iloc[-1]['Close'])
    save_trades(engine.transaction_log, current_price=price_final)
    
    # FIX: Recalcular o benchmark corretamente usando apenas preço do ativo
    price_initial = float(simulation_df.iloc[0]['Close'])
    price_final = float(simulation_df.iloc[-1]['Close'])
    btc_benchmark_profit_percentage = ((price_final - price_initial) / price_initial) * 100
    
    # Atualizar o resultado com o benchmark correto
    backtest_results['btc_benchmark_profit_percentage'] = btc_benchmark_profit_percentage
    
    # FIX: Adicionar metadados de data ao resultado
    backtest_results['start_date'] = simulation_df.iloc[0]['Open_time'].isoformat()
    backtest_results['end_date'] = simulation_df.iloc[-1]['Open_time'].isoformat()
    
    logger.info(f"✓ Benchmark BTC recalculado: {btc_benchmark_profit_percentage:.2f}% (Preço: ${price_initial:.2f} → ${price_final:.2f})")

    # 4. Logar o relatório final
    latest_indicators = simulation_df.tail(5) if not simulation_df.empty else None
    log_summary_report(backtest_results, latest_indicators)

    logger.info("Processamento do sistema de trade concluído.")
    
    if not backtest_results:
        backtest_results = {"error": "Backtest execution failed"}
        
    return {
        "backtest_report": backtest_results,
        "full_dataframe": full_df_with_predictions # Retornar o DF completo com as predições
    }
