# Em backend/src/system_runner.py
import logging
import pandas as pd
import os
# Orquestracao e backtest
from .data_provider import get_full_prepared_data
from .backtester import Backtester
from .strategies import run_strategy_regime_switcher
from .config import PROJECT_ROOT


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

    # Salva o relatorio em um arquivo .txt
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
        
        logger.info(f"Relatório de backtest salvo em: {report_path}")
        
    except Exception:
        logger.exception("Erro ao salvar o relatorio .txt")


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