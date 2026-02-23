import logging
import pandas as pd
import os

from backend.src.data.pipeline import get_full_prepared_data
from .core import TradingEngine
from .strategies import BTCLiteStrategy, AccumulatorStrategy
from .config import PROJECT_ROOT, ML_TRAIN_SPLIT_DATE
from .ai import train_prediction_model, get_predictions
from backend.src.data.storage import save_predictions_to_db, save_trades, save_simulation_summary
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


def run_trading_system(start_date: str = None, end_date: str = None, initial_capital: float = None):
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
    if start_date:
        start_ts = pd.Timestamp(start_date)
        simulation_df = simulation_df[simulation_df['Open_time'] >= start_ts].copy()
    if end_date:
        end_ts = pd.Timestamp(end_date)
        simulation_df = simulation_df[simulation_df['Open_time'] <= end_ts].copy()
    simulation_df = simulation_df.reset_index(drop=True)

    if simulation_df.empty:
        logger.error("Simulation window produced no data. Check start/end dates.")
        return {"backtest_report": {"error": "No data in simulation window"}, "full_dataframe": full_df_with_predictions}
    
    logger.info(f"Filtered simulation data. Starting from {split_date}. Rows: {len(simulation_df)}")
    logger.info(f"Fase 3: Configurando Backtest Walk-Forward...")
    logger.info(f"  TREINO (Training Set): até 2023-12-31 | Dataset: {full_df[full_df['Open_time'] < split_date].shape[0]:,} candles")
    logger.info(f"  TESTE (Backtest Set): {simulation_df['Open_time'].min().strftime('%Y-%m-%d')} até {simulation_df['Open_time'].max().strftime('%Y-%m-%d')} | Dataset: {len(simulation_df):,} candles")
    logger.info(f"  ✓ Cobertura do halving/ETFs (2024): Completamente incluída no backtest")
    logger.info(f"  Modelo foi treinado em dados anteriores a {ML_TRAIN_SPLIT_DATE}")
    
    # Configurar e Executar o Backtester apenas com dados pós-split
    logger.info("Fase 4: Executando o backtest da estratégia...")
    # Raised initial capital slightly to provide a healthier buffer for gas + liquidity
    engine_initial_capital = float(initial_capital) if initial_capital is not None else 1050.0
    engine = TradingEngine(initial_capital_usd=engine_initial_capital)
    
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
    
    # ========== PROBLEMA 2 FIX: Calcular total_equity ==========
    # O Dashboard deve mostrar o valor total dos ativos (Cash + BTC), não apenas o saldo em dólar
    btc_value = engine.btc_hodl_balance * price_final
    total_equity = engine.usd_balance + btc_value
    
    # Atualizar os resultados com o total equity
    # final_usd_value agora reflete o valor TOTAL da carteira (cash + BTC)
    backtest_results['final_usd_value'] = total_equity
    backtest_results['cash_balance'] = engine.usd_balance  # Saldo em dólar puro
    backtest_results['btc_amount'] = engine.btc_hodl_balance  # Quantidade de BTC
    backtest_results['btc_price_final'] = price_final  # Preço final do BTC
    
    # Recalcular ROI usando o total_equity para refletir corretamente a performance
    backtest_results['profit_usd'] = total_equity - engine.initial_capital
    backtest_results['profit_percentage_usd'] = ((total_equity / engine.initial_capital) - 1) * 100
    
    # ========== NOVAS MÉTRICAS: Token-Based Performance ==========
    # Calcular saldo inicial em tokens (BTC): quanto BTC teríamos se comprássemos tudo no início
    initial_token_balance = engine.initial_capital / price_initial
    
    # Calcular saldo final em tokens (BTC): quanto vale nosso patrimônio hoje em BTC
    final_token_balance = total_equity / price_final
    
    # Calcular ROI em tokens: variação percentual do saldo em tokens
    token_roi = ((final_token_balance - initial_token_balance) / initial_token_balance) * 100
    
    # Calcular Alpha vs HOLD: diferença entre ROI da estratégia e ROI do benchmark
    alpha_vs_hold = backtest_results['profit_percentage_usd'] - btc_benchmark_profit_percentage
    
    logger.info(
        f"✓ Total Equity Calculado: ${total_equity:.2f} "
        f"(Cash: ${engine.usd_balance:.2f} + BTC Value: ${btc_value:.2f})"
    )
    logger.info(f"✓ Benchmark BTC recalculado: {btc_benchmark_profit_percentage:.2f}% (Preço: ${price_initial:.2f} → ${price_final:.2f})")
    logger.info(
        f"✓ Token Metrics: Initial={initial_token_balance:.6f} BTC, "
        f"Final={final_token_balance:.6f} BTC, ROI={token_roi:.2f}%, "
        f"Alpha={alpha_vs_hold:.2f}%"
    )

    # ========== FASE 4c: PERSISTIR O SUMMARY OFICIAL ==========
    # Salvar os valores finais OFICIAIS no banco de dados para o Dashboard
    num_trades = len(engine.transaction_log) if engine.transaction_log else 0
    lp_total_value = 0.0
    lp_fees_usd = 0.0
    for lp in engine.active_lps:
        asset_value, _, _ = engine._get_lp_value(lp, price_final)
        asset_value = float(asset_value)
        fees_value = lp.get('fees_accrued_usdt', 0.0) + (lp.get('fees_accrued_btc', 0.0) * price_final)
        lp_total_value += asset_value + fees_value
        lp_fees_usd += fees_value

    wallet_spot_total_usd = engine.usd_balance + (engine.btc_hodl_balance * price_final)
    aave_collateral_usd = engine.btc_hodl_balance * price_final
    aave_debt_usd = engine.total_debt_usd
    aave_health_factor = engine.health_factor

    save_simulation_summary(
        total_equity=total_equity,
        roi_percent=backtest_results['profit_percentage_usd'],
        benchmark_roi_percent=btc_benchmark_profit_percentage,
        total_trades=num_trades,
        initial_capital=engine.initial_capital,
        cash_balance=engine.usd_balance,
        btc_amount=engine.btc_hodl_balance,
        btc_price_final=price_final,
        wallet_spot_total_usd=wallet_spot_total_usd,
        wallet_lp_value_usd=lp_total_value,
        lp_active_count=len(engine.active_lps),
        lp_fees_usd=lp_fees_usd,
        aave_collateral_usd=aave_collateral_usd,
        aave_debt_usd=aave_debt_usd,
        aave_health_factor=aave_health_factor,
        initial_token_balance=initial_token_balance,
        final_token_balance=final_token_balance,
        token_roi=token_roi,
        alpha_vs_hold=alpha_vs_hold
    )

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
