"""
Market Analytics Module

Provides year-by-year market analysis including returns, drawdowns,
explosive days, and other volatility metrics.
"""

import logging
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def calculate_yearly_metrics(df: pd.DataFrame) -> Dict[int, Dict[str, Any]]:
    """
    Analyzes a klines DataFrame and returns yearly market metrics.
    
    Input:
        df (pd.DataFrame): DataFrame with at least 'Open_time' and 'Close' columns.
                          Open_time should be datetime-like; Close should be numeric.
    
    Output:
        Dict[int, Dict]: Keyed by year (e.g., 2023, 2024).
                        Each year dict contains:
                        - 'total_return': ((last_price - first_price) / first_price) * 100
                        - 'max_drawdown': Maximum % drop from peak within year
                        - 'explosive_days_count': Days with daily return > 5%
                        - 'severe_dump_days_count': Days with daily return < -5%
                        - 'biggest_single_day_pump': Max daily return %
                        - 'daily_returns': List of daily % changes (for charting)
    """
    if df is None or df.empty:
        logger.warning("Input DataFrame is empty; returning empty result.")
        return {}
    
    # Ensure Open_time is datetime
    if 'Open_time' in df.columns:
        df = df.copy()
        df['Open_time'] = pd.to_datetime(df['Open_time'])
    else:
        logger.error("DataFrame missing 'Open_time' column.")
        return {}
    
    # Ensure Close is numeric
    if 'Close' not in df.columns:
        logger.error("DataFrame missing 'Close' column.")
        return {}
    
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df = df.dropna(subset=['Close'])
    
    # Extract year
    df['Year'] = df['Open_time'].dt.year
    
    # Calculate daily returns
    df['Daily_Return_Pct'] = df['Close'].pct_change() * 100
    
    result = {}
    
    for year in sorted(df['Year'].unique()):
        year_df = df[df['Year'] == year].copy()
        
        if year_df.empty:
            continue
        
        year_df = year_df.reset_index(drop=True)
        closes = year_df['Close'].values
        daily_returns = year_df['Daily_Return_Pct'].values
        
        # Metrics
        first_price = float(closes[0])
        last_price = float(closes[-1])
        total_return = ((last_price - first_price) / first_price) * 100 if first_price != 0 else 0.0
        
        # Max Drawdown
        cummax = pd.Series(closes).cummax()
        drawdown = (closes - cummax.values) / cummax.values * 100
        max_drawdown = float(drawdown.min())
        
        # Explosive days and dumps
        explosive_count = int((daily_returns > 5).sum())
        dump_count = int((daily_returns < -5).sum())
        
        # Biggest pump
        biggest_pump = float(daily_returns[1:].max()) if len(daily_returns) > 1 else 0.0
        
        # Store metrics
        result[year] = {
            'total_return': round(total_return, 2),
            'max_drawdown': round(max_drawdown, 2),
            'explosive_days_count': explosive_count,
            'severe_dump_days_count': dump_count,
            'biggest_single_day_pump': round(biggest_pump, 2),
            # Include daily returns for frontend charting
            'daily_returns': [round(float(r), 2) for r in daily_returns[1:]],  # Skip first NaN
            'first_price': round(first_price, 2),
            'last_price': round(last_price, 2),
            'candles_in_year': len(year_df),
        }
        
        logger.info(
            f"Year {year}: Return={result[year]['total_return']:.2f}%, "
            f"Drawdown={result[year]['max_drawdown']:.2f}%, "
            f"Explosive Days={explosive_count}"
        )
    
    return result
