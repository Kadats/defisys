import pandas as pd
import numpy as np
import logging
from backend.src.system_runner import train_model_pipeline
from backend.src.data.pipeline import get_full_prepared_data
from backend.src.data.storage.connection import create_connection
from backend.src.core.trading_engine import TradingEngine
from backend.src.core.policy_layer import PolicyLayerStrategy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Retrain_OOS_2026")

def calculate_metrics(engine, initial_price, final_price, df_len):
    equity_series = pd.Series(engine.portfolio_history)
    max_drawdown = 0.0
    sharpe_ratio = 0.0
    
    if not equity_series.empty:
        cummax = equity_series.cummax()
        drawdown = (cummax - equity_series) / cummax
        max_drawdown = float(drawdown.max() * 100)
        
        returns = equity_series.pct_change().dropna()
        if not returns.empty and returns.std() != 0:
            sharpe_ratio = float((returns.mean() / returns.std()) * np.sqrt(2190))
            
    roi_percentage = ((engine._calculate_portfolio_value(final_price) - engine.initial_capital) / engine.initial_capital) * 100
    btc_benchmark_profit_percentage = ((final_price - initial_price) / initial_price) * 100
    alpha_vs_hold = roi_percentage - btc_benchmark_profit_percentage
    
    return max_drawdown, sharpe_ratio, alpha_vs_hold, roi_percentage

def main():
    logger.info("INICIANDO RETREINAMENTO GLOBAL (2017 a 2025)...")
    train_results = train_model_pipeline()
    logger.info(f"Treinamento concluido! Métricas: {train_results}")
    
    logger.info("\nPREPARANDO DADOS PARA BACKTEST OOS 2026...")
    try:
        from backend.src.data.pipeline import get_predictions_from_db
        predictions_df = get_predictions_from_db()
    except Exception:
        conn = create_connection()
        predictions_df = pd.read_sql_query("SELECT open_time, prediction, prediction_proba FROM model_predictions", conn)
        conn.close()

    market_df = get_full_prepared_data()

    if market_df.empty or predictions_df.empty:
        logger.error("Dados ou predições insuficientes.")
        return

    # Merge
    market_df['Open_time'] = pd.to_datetime(market_df['Open_time'])
    predictions_df.rename(columns={'open_time': 'Open_time'}, inplace=True)
    predictions_df['Open_time'] = pd.to_datetime(predictions_df['Open_time'])
    df = pd.merge(market_df, predictions_df[['Open_time', 'prediction', 'prediction_proba']], on='Open_time', how='left')

    # Filtrar apenas 2026 em diante
    df = df[df['Open_time'] >= pd.Timestamp('2026-01-01')].copy()
    df['prediction_proba'] = df['prediction_proba'].fillna(0.5)

    if 'FGI_Drop_24h' not in df.columns and 'Fear_Greed_Index' in df.columns:
        df['FGI_Drop_24h'] = df['Fear_Greed_Index'].shift(6) - df['Fear_Greed_Index']
        df['FGI_Drop_24h'] = df['FGI_Drop_24h'].fillna(0)

    logger.info(f"\n==================================================")
    logger.info(f"RODANDO TESTE OOS: 2026-01-01 até o presente")
    logger.info(f"Tamanho do dataset (velas): {len(df)}")
    logger.info(f"==================================================\n")
    
    engine = TradingEngine(initial_capital_usd=1000.0)
    strategy = PolicyLayerStrategy()
    
    results = engine.run(df.reset_index(drop=True), strategy)
    
    initial_price = float(df.iloc[0]['Close'])
    final_price = float(df.iloc[-1]['Close'])
    
    max_drawdown, sharpe_ratio, alpha_vs_hold, roi_percentage = calculate_metrics(engine, initial_price, final_price, len(df))
    
    logger.info(f"Capital Inicial: $1000.00")
    logger.info(f"Capital Final: ${engine._calculate_portfolio_value(final_price):.2f}")
    logger.info(f"ROI Estratégia: {roi_percentage:.2f}%")
    logger.info(f"Alpha vs USD (HOLD BTC): {alpha_vs_hold:.2f}%")
    logger.info(f"Max Drawdown: {max_drawdown:.2f}%")
    logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    logger.info(f"Total Trades: {len(engine.transaction_log)}")

if __name__ == '__main__':
    main()