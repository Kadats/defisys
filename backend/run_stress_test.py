import pandas as pd
from backend.src.data.pipeline import get_predictions_from_db, get_full_prepared_data
from backend.src.core.trading_engine import TradingEngine
from backend.src.strategies.smart_dca import SmartDCAStrategy
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StressTest")

def main():
    logger.info("Carregando predições e dados de mercado...")
    predictions_df = get_predictions_from_db()
    market_df = get_full_prepared_data()

    if market_df.empty or predictions_df.empty:
        logger.error("Dados ou predições insuficientes.")
        return

    # Merge
    market_df['Open_time'] = pd.to_datetime(market_df['Open_time'])
    predictions_df.rename(columns={'open_time': 'Open_time'}, inplace=True)
    predictions_df['Open_time'] = pd.to_datetime(predictions_df['Open_time'])
    df = pd.merge(market_df, predictions_df[['Open_time', 'prediction', 'prediction_proba']], on='Open_time', how='left')

    # Filtrar últimos 365 dias
    max_date = df['Open_time'].max()
    min_date = max_date - pd.Timedelta(days=365)
    simulation_df = df[df['Open_time'] >= min_date].copy().reset_index(drop=True)

    logger.info(f"Simulação para os últimos 365 dias (de {simulation_df['Open_time'].min()} até {max_date})")
    logger.info(f"Total de candles: {len(simulation_df)}")

    logger.info("Configurando TradingEngine com Stress Parameters: Gas=$80.0, Slippage=3% (0.03)")
    engine = TradingEngine(initial_capital_usd=1000.0, gas_fee_usd=80.0, slippage_pct=0.03)
    
    strategy = SmartDCAStrategy()
    
    logger.info("Iniciando backtest...")
    results = engine.run(simulation_df, strategy)
    
    logger.info("\n====================================")
    logger.info("      RESULTADOS DO BACKTEST")
    logger.info("====================================")
    logger.info(f"Initial Capital: ${results['initial_capital_usd']:.2f}")
    logger.info(f"Final Value:     ${results['final_usd_value']:.2f}")
    logger.info(f"Profit USD:      ${results['profit_usd']:.2f}")
    logger.info(f"Profit %:        {results['profit_percentage_usd']:.2f}%")
    logger.info(f"BTC Benchmark %: {results['btc_benchmark_profit_percentage']:.2f}%")
    logger.info("====================================\n")

if __name__ == '__main__':
    main()
