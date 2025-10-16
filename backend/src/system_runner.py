import logging

# Orquestracao e backtest
from .data_provider import get_full_prepared_data
from .backtester import run_backtest
from .logging_config import setup_logging
from .config import LOG_LEVEL

logger = logging.getLogger(__name__)


def log_summary_report(results, latest_indicators=None):
    """Registra um resumo simples do relatorio de backtest e indicadores recentes."""
    try:
        logger.info("--- RELATORIO DE BACKTEST ---")
        logger.info("Capital Inicial: $%0.2f", results.get('initial_capital_usd'))
        logger.info("Capital Final: $%0.2f", results.get('final_usd_value'))
        logger.info("Lucro/Prejuizo: $%0.2f (%0.2f%%)", results.get('profit_usd'), results.get('profit_percentage_usd'))
        logger.info("Performance do Buy and Hold (BTC): (%0.2f%%)", results.get('btc_benchmark_profit_percentage'))

        if latest_indicators is not None:
            logger.info("--- INDICADORES RECENTES ---")
            logger.info("%s", str(latest_indicators))
    except Exception:
        logger.exception("Erro ao logar o sumario do relatorio")


def run_trading_system():
    """
    Orquestra o fluxo de alto nivel: solicita os dados preparados e executa o backtest.
    """
    # Obter o DataFrame com todos os dados e indicadores prontos
    all_klines_df = get_full_prepared_data()

    if all_klines_df is None or all_klines_df.empty:
        logger.warning("Nao ha dados preparados para executar o backtest.")
        return {"backtest_report": {}, "full_dataframe": all_klines_df}

    # Executa o backtest
    initial_capital = 1000
    backtest_results = run_backtest(all_klines_df, initial_capital_usd=initial_capital)

    # Log resumido
    # Pega ultimas linhas para resumir indicadores recentes
    latest_indicators = None
    try:
        latest_indicators = all_klines_df.dropna().tail(5)[['Open_time', 'Close', 'SMA_20', 'EMA_20', 'MACD', 'MACD_Signal']]
    except Exception:
        latest_indicators = None

    log_summary_report(backtest_results, latest_indicators)

    return {"backtest_report": backtest_results, "full_dataframe": all_klines_df}
