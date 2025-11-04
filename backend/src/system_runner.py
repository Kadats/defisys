# Em backend/src/system_runner.py
import logging
import pandas as pd
# Orquestracao e backtest
from .data_provider import get_full_prepared_data # Corrigido para importar da toolkit
from .backtester import Backtester # Importa a CLASSE
from .strategies import run_strategy_regime_switcher # Importa a FUNÇÃO da estratégia
# (Remova imports não usados como run_backtest antigo, config, logging_config se não forem usados aqui)


logger = logging.getLogger(__name__)

# (A função log_summary_report permanece a mesma)
def log_summary_report(results, latest_indicators=None):
    """Registra um resumo simples do relatorio de backtest e indicadores recentes."""
    try:
        logger.info("--- RELATORIO DE BACKTEST (v2 Engine) ---")
        logger.info("Capital Inicial: $%0.2f", results.get('initial_capital_usd'))
        logger.info("Capital Final: $%0.2f", results.get('final_usd_value'))
        logger.info("Lucro/Prejuizo: $%0.2f (%0.2f%%)", results.get('profit_usd'), results.get('profit_percentage_usd'))
        logger.info("Performance do Buy and Hold (BTC): (%0.2f%%)", results.get('btc_benchmark_profit_percentage'))

        if latest_indicators is not None:
             # Ajustado para mostrar scores, se disponíveis
            cols_to_show = ['Open_time', 'Close', 'Sentimento_Score', 'Volatilidade_Score', 'Oportunidade_Score']
            cols_available = [col for col in cols_to_show if col in latest_indicators.columns]
            logger.info("--- INDICADORES RECENTES ---")
            logger.info("\n%s", latest_indicators[cols_available].to_string())
    except Exception:
        logger.exception("Erro ao logar o sumario do relatorio")


def run_trading_system():
    """
    Orquestra o fluxo de alto nivel usando o novo Backtester Engine.
    """
    logger.info("Iniciando o sistema de trade...")

    # 1. Obter os dados já preparados
    logger.info("Fase 1: Preparando todos os dados de mercado e indicadores...")
    # Corrigido: Usar a função correta do data_provider da toolkit
    full_df = get_full_prepared_data() 
    if full_df is None or full_df.empty:
        logger.error("Não foi possível obter os dados para o backtest. Encerrando.")
        # Retorna estrutura compatível com a API
        return {"backtest_report": {"error": "Failed to get data"}, "full_dataframe": pd.DataFrame()} 

    # 2. Configurar e Executar o Backtester v2
    logger.info("Fase 2: Executando o backtest da estratégia v1...")
    initial_capital = 1000.0
    engine = Backtester(initial_capital_usd=initial_capital)
    
    # Passa o DataFrame E a função da estratégia para o motor
    backtest_results = engine.run(full_df, strategy_function=run_strategy_regime_switcher) 

    # 3. Logar o relatório final
    latest_indicators = full_df.tail(5) if not full_df.empty else None
    log_summary_report(backtest_results, latest_indicators)

    logger.info("Processamento do sistema de trade concluído.")

    # 4. Retornar os resultados para a API
    # Garantir que o dataframe retornado é compatível com JSON (pode precisar de sanitização como na api.py)
    # Vamos assumir que a sanitização acontece na api.py por enquanto
    
    # Verifica se backtest_results não está vazio antes de retornar
    if not backtest_results:
        backtest_results = {"error": "Backtest execution failed"}
        
    return {
        "backtest_report": backtest_results,
        "full_dataframe": full_df # Continuamos a retornar o DF completo
    }