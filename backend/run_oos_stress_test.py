import pandas as pd
import numpy as np
import logging
from backend.src.data.pipeline import get_full_prepared_data
from backend.src.data.storage.connection import create_connection
from backend.src.core.trading_engine import TradingEngine
from backend.src.core.policy_layer import PolicyLayerStrategy
from backend.src.config import ML_TRAIN_SPLIT_DATE

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OOS_StressTest")

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
            # Annualized Sharpe (assuming 6 4h-candles per day, 365 days = 2190 candles/year)
            sharpe_ratio = float((returns.mean() / returns.std()) * np.sqrt(2190))
            
    roi_percentage = ((engine._calculate_portfolio_value(final_price) - engine.initial_capital) / engine.initial_capital) * 100
    btc_benchmark_profit_percentage = ((final_price - initial_price) / initial_price) * 100
    alpha_vs_hold = roi_percentage - btc_benchmark_profit_percentage
    
    return max_drawdown, sharpe_ratio, alpha_vs_hold, roi_percentage

def run_period(name, df, start_date, end_date):
    logger.info(f"\n{'='*50}\nRodando Teste OOS: {name}\nPeriodo: {start_date} a {end_date}\n{'='*50}")
    
    mask = (df['Open_time'] >= start_date) & (df['Open_time'] <= end_date)
    period_df = df[mask].copy().reset_index(drop=True)
    
    if period_df.empty:
        logger.error(f"Sem dados para o periodo {name}.")
        return
        
    engine = TradingEngine(initial_capital_usd=1000.0)
    strategy = PolicyLayerStrategy()
    
    results = engine.run(period_df, strategy)
    
    initial_price = float(period_df.iloc[0]['Close'])
    final_price = float(period_df.iloc[-1]['Close'])
    
    max_drawdown, sharpe_ratio, alpha_vs_hold, roi_percentage = calculate_metrics(engine, initial_price, final_price, len(period_df))
    
    logger.info(f"Capital Inicial: $1000.00")
    logger.info(f"Capital Final: ${engine._calculate_portfolio_value(final_price):.2f}")
    logger.info(f"ROI Estratégia: {roi_percentage:.2f}%")
    logger.info(f"Alpha vs USD (HOLD BTC): {alpha_vs_hold:.2f}%")
    logger.info(f"Max Drawdown: {max_drawdown:.2f}%")
    logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    logger.info(f"Total Trades: {len(engine.transaction_log)}")

def main():
    logger.info("Carregando predições e dados de mercado...")
    
    try:
        from backend.src.data.pipeline import get_predictions_from_db
        predictions_df = get_predictions_from_db()
    except Exception:
        # Fallback to direct query
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

    # Garantir que só estamos usando dados OOS (após o ML_TRAIN_SPLIT_DATE = 2023-12-31)
    df = df[df['Open_time'] > pd.Timestamp('2023-12-31')].copy()

    # Preencher NaNs no prediction (caso não haja predição)
    df['prediction_proba'] = df['prediction_proba'].fillna(0.5)

    # Adicionar FGI_Drop_24h mockado para o teste caso não exista
    if 'FGI_Drop_24h' not in df.columns and 'Fear_Greed_Index' in df.columns:
        # Simplistic mock: difference over last 6 candles (24h for 4h timeframe)
        df['FGI_Drop_24h'] = df['Fear_Greed_Index'].shift(6) - df['Fear_Greed_Index']
        df['FGI_Drop_24h'] = df['FGI_Drop_24h'].fillna(0)

    # Executar Cenários
    run_period("Abril/2024 (Halving Volatility)", df, "2024-04-01", "2024-04-30")
    run_period("Agosto/2024 (Crash Global)", df, "2024-08-01", "2024-08-31")
    run_period("Março/2026 (Volatilidade Recente)", df, "2026-03-01", "2026-03-31")
    
    # Executar OOS completo
    run_period("Full OOS (2024-2026)", df, "2024-01-01", "2026-12-31")

if __name__ == '__main__':
    main()