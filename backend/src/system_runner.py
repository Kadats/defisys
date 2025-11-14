import logging
import pandas as pd
import os

from .data_provider import get_full_prepared_data
from .backtester import Backtester
from .strategies import run_strategy_regime_switcher
from .config import PROJECT_ROOT
from .prediction_engine import train_prediction_model, get_predictions
from defi_data_toolkit.database import save_predictions_to_db
from .config import PROJECT_ROOT, DB_FILE

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

    # --- Parte 2: Salvar Relatório em Arquivo .txt (MANTIDA) ---
    try:
        report_path = os.path.join(PROJECT_ROOT, "backtest_report.txt")
        decision_history = results.get('decision_history', [])
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("--- RELATORIO DE BACKTEST (v2 Engine) ---\n")
            f.write(f"Data da Execução: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*40 + "\n")
            f.write(f"Capital Inicial: ${results.get('initial_capital_usd'):.2f}\n")
            f.write(f"Capital Final: ${results.get('final_usd_value'):.2f}\n")
            f.write(f"Lucro/Prejuizo: ${results.get('profit_usd'):.2f} ({results.get('profit_percentage_usd'):.2f}%)\n")
            f.write(f"Performance do Buy and Hold (BTC): {results.get('btc_benchmark_profit_percentage'):.2f}%\n")
            f.write("\n" + "="*40 + "\n")
            f.write("--- HISTORICO DE DECISOES ---\n\n")
            
            if decision_history:
                for decision in decision_history:
                    f.write(f"{decision}\n")
            else:
                f.write("Nenhuma decisão foi tomada.\n")
        
        # Manter este log para sabermos que o arquivo foi salvo
        logger.info(f"Relatório de backtest salvo em: {report_path}")
        
    except Exception:
        logger.exception("Erro ao salvar o relatorio .txt")


def run_trading_system():
    """
    Orquestra o fluxo de alto nivel: Dados -> Modelo de ML -> Backtest.
    """
    logger.info("Iniciando o sistema de trade...")

    # 1. Obter os dados (agora com features e alvos de ML)
    logger.info("Fase 1: Preparando todos os dados de mercado e indicadores...")
    full_df = get_full_prepared_data() 
    if full_df is None or full_df.empty:
        logger.error("Não foi possível obter os dados. Encerrando.")
        return {"backtest_report": {"error": "Failed to get data"}, "full_dataframe": pd.DataFrame()} 

    # --- MUDANÇA 2: Treinar o Modelo de ML ---
    logger.info("Fase 2: Treinando o modelo de predição...")
    model, scaler = train_prediction_model(full_df)
    
    # Gerar predições para todo o histórico (para análise)
    full_df_with_predictions = get_predictions(model, scaler, full_df)

    # --- Salvar as predições no DB ---
    logger.info("Fase 2b: Salvando predições no banco de dados...")
    save_predictions_to_db(full_df_with_predictions, DB_FILE)

    # 3. Configurar e Executar o Backtester
    logger.info("Fase 3: Executando o backtest da estratégia...")
    initial_capital = 1000.0
    engine = Backtester(initial_capital_usd=initial_capital)
    
    # O backtester roda no DataFrame que agora contém as predições
    backtest_results = engine.run(full_df_with_predictions, strategy_function=run_strategy_regime_switcher) 

    # 4. Logar o relatório final
    latest_indicators = full_df_with_predictions.tail(5) if not full_df_with_predictions.empty else None
    log_summary_report(backtest_results, latest_indicators)

    logger.info("Processamento do sistema de trade concluído.")
    
    if not backtest_results:
        backtest_results = {"error": "Backtest execution failed"}
        
    return {
        "backtest_report": backtest_results,
        "full_dataframe": full_df_with_predictions # Retornar o DF com as predições
    }
