"""
Data Pipeline - Orchestrates data collection, storage, and indicator calculation.

This module replaces data_provider.py and coordinates the flow of data from
API sources through storage to indicator calculation.
"""

import logging
import warnings
import pandas as pd
import numpy as np

# Suppress pandas SQLAlchemy warnings about using psycopg2 directly
warnings.filterwarnings('ignore', category=UserWarning, module='pandas')
from datetime import datetime, timedelta
from typing import Optional

from backend.src.data import sources, storage
from backend.src.utils import indicators
from backend.src.config import (
    DEFAULT_SYMBOL,
    DEFAULT_INTERVAL,
    DEFAULT_HISTORICAL_DAYS,
    DEFAULT_KLINES_LIMIT,
    BINANCE_API_BASE_URL,
    BINANCE_FUTURES_API_BASE_URL,
    FNG_API_URL,
    BLOCKCHAIR_API_URL,
    DERIBIT_API_BASE_URL,
    THEGRAPH_UNISWAP_V3_URL,
    THEGRAPH_API_KEY,
    THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS,
    DEFAULT_NETWORK,
    DEFAULT_POLYGON_POOL_ID,
)

logger = logging.getLogger(__name__)

# ML Constants
PREDICTION_HORIZON_DAYS = 7
PREDICTION_RISE_THRESHOLD = 0.015  # +1.5% rise for bullish signal (V12: Lower threshold to catch slow bull markets)


def get_full_prepared_data() -> pd.DataFrame:
    """
    Orchestrates Phases 1-4: collection, persistence, indicator calculation,
    data merging and ML preparation.
    
    Returns:
        pd.DataFrame: Prepared data with all features and target for ML training
    """
    
    # Define table names
    klines_table_name = f"{DEFAULT_SYMBOL}_{DEFAULT_INTERVAL}_klines".lower()
    fng_table_name = "fear_and_greed_index"
    on_chain_table_name = "bitcoin_on_chain_metrics"
    funding_rate_table_name = "binance_futures_funding_rate"
    open_interest_table_name = "binance_futures_open_interest"
    implied_vol_table_name = "implied_volatility"
    uniswap_table_name = "uniswap_pool_data"

    conn = storage.create_connection()
    if conn:
        try:
            storage.create_klines_table(conn, klines_table_name)
            storage.create_fng_table(conn, fng_table_name)
            storage.create_on_chain_table(conn, on_chain_table_name)
            storage.create_funding_rate_table(conn, funding_rate_table_name)
            storage.create_open_interest_table(conn, open_interest_table_name)
            storage.create_implied_volatility_table(conn, implied_vol_table_name)
            storage.create_uniswap_pool_table(conn, uniswap_table_name)
            storage.create_positions_log_table(conn)
            storage.create_ml_predictions_table(conn)
        finally:
            conn.close()
    
    # ===== PHASE 1: DATA COLLECTION =====
    logger.info(f"Starting collection/preparation process for {DEFAULT_SYMBOL} ({DEFAULT_INTERVAL})...")
    
    # 1. Collect Klines with pagination
    start_ts_klines = storage.get_start_timestamp_for_collection(
        storage.get_last_timestamp_from_db, klines_table_name, DEFAULT_HISTORICAL_DAYS
    )
    end_ts_klines = int(datetime.now().timestamp() * 1000)
    
    start_date = datetime.fromtimestamp(start_ts_klines / 1000)
    end_date = datetime.fromtimestamp(end_ts_klines / 1000)
    logger.info(f"Collecting {DEFAULT_SYMBOL} {DEFAULT_INTERVAL} klines with pagination...")
    logger.info(f"  Period: {start_date.strftime('%Y-%m-%d %H:%M:%S')} to {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if start_ts_klines < end_ts_klines:
        klines_df = sources.fetch_all_klines(
            DEFAULT_SYMBOL, DEFAULT_INTERVAL, start_ts_klines, end_ts_klines,
            max_klines_per_request=DEFAULT_KLINES_LIMIT,
            binance_api_base_url=BINANCE_API_BASE_URL
        )
        
        if not klines_df.empty:
            logger.info(f"✓ Collected {len(klines_df)} klines successfully")
            storage.save_klines_to_db(klines_df, klines_table_name)
            logger.info(f"✓ Klines saved to database (table: {klines_table_name})")
        else:
            logger.warning("No klines collected (empty DataFrame)")
    else:
        logger.warning("No new klines collected (invalid timestamps)")
    
    # 2. Collect Fear & Greed
    start_ts_fng_sec = storage.get_start_timestamp_for_collection(
        storage.get_last_fng_timestamp_from_db, fng_table_name, DEFAULT_HISTORICAL_DAYS
    )
    fng_data = sources.get_fear_and_greed_index(
        limit=DEFAULT_HISTORICAL_DAYS, start_date_unix_sec=start_ts_fng_sec, fng_api_url=FNG_API_URL
    )
    if fng_data:
        storage.save_fng_to_db(fng_data, fng_table_name)
    
    # 3. Collect On-Chain (Blockchair)
    on_chain_data = sources.get_bitcoin_network_fees(blockchair_api_url=BLOCKCHAIR_API_URL)
    if on_chain_data:
        storage.save_on_chain_to_db(on_chain_data, on_chain_table_name)
    
    # 4. Collect Funding Rate
    funding_data = sources.get_funding_rate_history(
        DEFAULT_SYMBOL, limit=100, binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL
    )
    if funding_data:
        storage.save_funding_rate_to_db(funding_data, funding_rate_table_name)
    
    # 5. Collect Open Interest
    oi_data = sources.get_open_interest(DEFAULT_SYMBOL, binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL)
    if oi_data:
        storage.save_open_interest_to_db(oi_data, open_interest_table_name)
    
    # 6. Collect Implied Volatility (Deribit)
    start_ts_iv = storage.get_start_timestamp_for_collection(
        storage.get_last_implied_volatility_timestamp_from_db, implied_vol_table_name, DEFAULT_HISTORICAL_DAYS
    )
    iv_data = sources.get_implied_volatility_history(start_timestamp_ms=start_ts_iv, deribit_base_url=DERIBIT_API_BASE_URL)
    if iv_data:
        storage.save_implied_volatility_to_db(iv_data, implied_vol_table_name)
    
    # 7. Collect Uniswap Pool Data
    start_ts_uni = storage.get_start_timestamp_for_collection(
        storage.get_last_uniswap_timestamp_from_db, uniswap_table_name, DEFAULT_HISTORICAL_DAYS
    )
    uni_data = sources.get_uniswap_pool_daily_data(
        pool_id=DEFAULT_POLYGON_POOL_ID,
        start_timestamp_ms=start_ts_uni,
        thegraph_base_url=THEGRAPH_UNISWAP_V3_URL,
        thegraph_api_key=THEGRAPH_API_KEY,
        thegraph_subgraph_ids=THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS,
        default_network=DEFAULT_NETWORK
    )
    if uni_data:
        storage.save_uniswap_pool_data_to_db(uni_data, uniswap_table_name)
    
    # ===== PHASE 2: LOAD DATA AND CALCULATE INDICATORS =====
    all_klines_df = storage.get_data_from_db(klines_table_name)
    if all_klines_df.empty:
        logger.warning("No sufficient data in database to continue.")
        return pd.DataFrame()
    
    logger.info(f"Klines DataFrame loaded with {len(all_klines_df)} klines for calculation.")
    
    # Calculate minimal indicator set (feature selection)
    # 1. Momentum
    all_klines_df['RSI'] = indicators.calculate_rsi(all_klines_df, column='Close', window=14)

    # 2. Trend (EMA50 distance)
    all_klines_df['EMA_50'] = indicators.calculate_ema(all_klines_df, column='Close', window=50)

    # 3. Volatility (Bollinger Band Width)
    bb_df = indicators.calculate_bollinger_bands(all_klines_df, column='Close', window=20)
    all_klines_df['BB_Middle'] = bb_df['BB_Middle']
    all_klines_df['BB_Upper'] = bb_df['BB_Upper']
    all_klines_df['BB_Lower'] = bb_df['BB_Lower']
    bb_middle_safe = all_klines_df['BB_Middle'].replace(0, np.nan)
    all_klines_df['BB_Width'] = (all_klines_df['BB_Upper'] - all_klines_df['BB_Lower']) / bb_middle_safe
    
    # ===== PHASE 3: MERGE AUXILIARY DATA SOURCES =====
    # Load auxiliary data
    conn = storage.create_connection()
    if not conn:
        logger.error("Failed to connect to database for auxiliary data")
        return pd.DataFrame()
    
    try:
        funding_rate_df = pd.read_sql(f"SELECT funding_time, funding_rate FROM {funding_rate_table_name}", conn)
        open_interest_df = pd.read_sql(f"SELECT timestamp, open_interest FROM {open_interest_table_name}", conn)
    except Exception as e:
        logger.warning(f"Failed to load funding/OI data: {e}")
        funding_rate_df = pd.DataFrame()
        open_interest_df = pd.DataFrame()
    finally:
        conn.close()
    
    uniswap_df = storage.get_uniswap_pool_data_from_db(uniswap_table_name)
    
    # Merge Sentiment (Funding + OI)
    if not funding_rate_df.empty and not open_interest_df.empty:
        funding_rate_df['Timestamp'] = pd.to_datetime(funding_rate_df['funding_time'], unit='ms')
        open_interest_df['Timestamp'] = pd.to_datetime(open_interest_df['timestamp'], unit='ms')
        
        sentiment_data_df = pd.merge(
            funding_rate_df[['Timestamp', 'funding_rate']], 
            open_interest_df[['Timestamp', 'open_interest']], 
            on='Timestamp', how='outer'
        ).sort_values(by='Timestamp').ffill().dropna()
        
        if not sentiment_data_df.empty:
            sentiment_data_df['Sentimento_Score'] = indicators.calculate_composite_sentiment(
                sentiment_data_df['funding_rate'], sentiment_data_df['open_interest']
            )
            all_klines_df['Date'] = all_klines_df['Open_time'].dt.date
            sentiment_data_df['Date'] = sentiment_data_df['Timestamp'].dt.date
            daily_sentiment = sentiment_data_df.groupby('Date').last().reset_index()
            
            cols_to_merge = ['Date', 'Sentimento_Score', 'funding_rate', 'open_interest']
            cols_to_merge = [c for c in cols_to_merge if c in daily_sentiment.columns]
            all_klines_df = pd.merge(all_klines_df, daily_sentiment[cols_to_merge], on='Date', how='left')
            
            # Fill empty values
            if 'funding_rate' in all_klines_df.columns:
                all_klines_df['FundingRate'] = all_klines_df['funding_rate'].ffill().bfill()
                all_klines_df.drop(columns=['funding_rate'], inplace=True)
            if 'open_interest' in all_klines_df.columns:
                all_klines_df['OpenInterest'] = all_klines_df['open_interest'].ffill().bfill()
                all_klines_df.drop(columns=['open_interest'], inplace=True)
            if 'Sentimento_Score' in all_klines_df.columns:
                all_klines_df['Sentimento_Score'] = all_klines_df['Sentimento_Score'].ffill().bfill()
            
            if 'Date' in all_klines_df.columns:
                all_klines_df.drop(columns=['Date'], inplace=True)
    else:
        logger.warning("No funding/open interest data available; filling FundingRate/OpenInterest with 0.")
        all_klines_df['FundingRate'] = 0.0
        all_klines_df['OpenInterest'] = 0.0

    # Ensure FundingRate/OpenInterest exist even if merge produced partial columns
    if 'FundingRate' not in all_klines_df.columns:
        all_klines_df['FundingRate'] = 0.0
    if 'OpenInterest' not in all_klines_df.columns:
        all_klines_df['OpenInterest'] = 0.0
    
    # Merge Uniswap Pool Data (VolumeUSD only) with safe fallback
    if not uniswap_df.empty:
        try:
            if 'VolumeUSD' not in uniswap_df.columns:
                logger.warning("Uniswap data missing 'VolumeUSD'. Filling with 0.")
                uniswap_df['VolumeUSD'] = 0.0
            if 'TVL_USD' not in uniswap_df.columns:
                logger.warning("Uniswap data missing 'TVL_USD'. Filling with 0.")
                uniswap_df['TVL_USD'] = 0.0

            uniswap_df['Date'] = uniswap_df['Timestamp'].dt.date
            daily_uniswap = uniswap_df.groupby('Date').last().reset_index()[['Date', 'VolumeUSD', 'TVL_USD']]
            all_klines_df['Date'] = all_klines_df['Open_time'].dt.date
            all_klines_df = pd.merge(all_klines_df, daily_uniswap, on='Date', how='left')
            all_klines_df['VolumeUSD'] = all_klines_df['VolumeUSD'].ffill().bfill()
            all_klines_df['TVL_USD'] = all_klines_df['TVL_USD'].ffill().bfill()
            if 'Date' in all_klines_df.columns:
                all_klines_df.drop(columns=['Date'], inplace=True)
        except Exception as e:
            logger.warning(f"Failed to merge Uniswap data: {e}. Filling VolumeUSD/TVL_USD with 0.")
            all_klines_df['VolumeUSD'] = 0.0
            all_klines_df['TVL_USD'] = 0.0
    else:
        logger.warning("No Uniswap data available; setting VolumeUSD/TVL_USD to 0.")
        all_klines_df['VolumeUSD'] = 0.0
        all_klines_df['TVL_USD'] = 0.0
    
    # ===== PHASE 4: ML DATA PREPARATION =====
    try:
        # 1. Feature Engineering
        all_klines_df['dist_from_ema_50'] = (all_klines_df['Close'] - all_klines_df['EMA_50']) / all_klines_df['EMA_50']

        # 2. Create Target (trend over next 12 candles / 48h)
        future_close = all_klines_df['Close'].shift(-12)
        log_return = np.log(future_close / all_klines_df['Close'])
        all_klines_df['Target_Trend'] = (log_return > 0.02).astype(int)

        # 3. Clean data
        REQUIRED_COLUMNS = [
            'RSI', 'dist_from_ema_50', 'BB_Width',
            'FundingRate', 'OpenInterest', 'VolumeUSD',
            'Target_Trend'
        ]
        
        # Only keep columns that exist
        existing_required = [col for col in REQUIRED_COLUMNS if col in all_klines_df.columns]
        all_klines_df = all_klines_df.dropna(subset=existing_required)
        logger.info(f"Feature and Target columns created. Total of {len(all_klines_df)} training samples ready.")
        
    except Exception as e:
        logger.error(f"Failed to create features/target for ML model: {e}")
        return pd.DataFrame()
    
    return all_klines_df


def get_positions_from_db(include_open: bool = True, include_closed: bool = True) -> pd.DataFrame:
    """Loads position log (open and/or closed) from database."""
    conn = storage.create_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        base_query = "SELECT * FROM positions_log"
        conditions = []
        if include_open and not include_closed:
            conditions.append("close_timestamp IS NULL")
        elif include_closed and not include_open:
            conditions.append("close_timestamp IS NOT NULL")
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        base_query += " ORDER BY open_timestamp DESC"
        
        df = pd.read_sql(base_query, conn)
        
        if not df.empty:
            df['open_timestamp'] = pd.to_datetime(df['open_timestamp'], unit='ms')
            if 'close_timestamp' in df.columns:
                df['close_timestamp'] = pd.to_datetime(df['close_timestamp'], unit='ms', errors='coerce')
        
        return df
    
    except Exception as e:
        logger.error(f"Error reading 'positions_log' from DB: {e}. Table may not exist yet.")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def get_predictions_from_db() -> pd.DataFrame:
    """Loads ML predictions (timestamp, prediction, prediction_correct) from DB."""
    conn = storage.create_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        base_query = "SELECT * FROM ml_predictions ORDER BY open_time ASC"
        df = pd.read_sql(base_query, conn)
        
        if not df.empty:
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        
        return df
    
    except Exception as e:
        logger.warning(f"Error reading 'ml_predictions' from DB: {e}. Table may not exist.")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()
