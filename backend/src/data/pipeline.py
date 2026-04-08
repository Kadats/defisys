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
    ML_PREDICTION_HORIZON,
    ML_TARGET_MIN_CHANGE,
)

logger = logging.getLogger(__name__)

# ML Constants
PREDICTION_HORIZON_DAYS = 7
PREDICTION_RISE_THRESHOLD = 0.015  # +1.5% rise for bullish signal (V12: Lower threshold to catch slow bull markets)


def sync_market_data() -> None:
    """
    Phase 1: Data Fetching - Synchronizes market data from external APIs to the database.
    
    This function:
    - Creates all necessary database tables
    - Fetches missing klines from Binance
    - Updates Fear & Greed Index
    - Updates On-chain metrics (Blockchair)
    - Updates Funding Rate (Binance Futures)
    - Updates Open Interest (Binance Futures)
    - Updates Implied Volatility (Deribit)
    - Updates Uniswap Pool Data (TheGraph)
    
    This function does NOT:
    - Calculate indicators
    - Prepare ML features/targets
    - Train models
    - Run backtests
    
    Should be called on FastAPI startup to ensure fresh data.
    """
    logger.info("=" * 80)
    logger.info("🔄 INICIANDO SINCRONIZAÇÃO DE DADOS DE MERCADO NO STARTUP...")
    logger.info("=" * 80)
    
    # Define table names
    klines_table_name = f"{DEFAULT_SYMBOL}_{DEFAULT_INTERVAL}_klines".lower()
    fng_table_name = "fear_and_greed_index"
    on_chain_table_name = "bitcoin_on_chain_metrics"
    funding_rate_table_name = "binance_futures_funding_rate"
    open_interest_table_name = "binance_futures_open_interest"
    implied_vol_table_name = "implied_volatility"
    uniswap_table_name = "uniswap_pool_data"

    # Create all database tables
    conn = storage.create_connection()
    if conn:
        try:
            logger.info("📊 Verificando/criando tabelas no banco de dados...")
            storage.create_klines_table(conn, klines_table_name)
            storage.create_fng_table(conn, fng_table_name)
            storage.create_on_chain_table(conn, on_chain_table_name)
            storage.create_funding_rate_table(conn, funding_rate_table_name)
            storage.create_open_interest_table(conn, open_interest_table_name)
            storage.create_implied_volatility_table(conn, implied_vol_table_name)
            storage.create_uniswap_pool_table(conn, uniswap_table_name)
            storage.create_positions_log_table(conn)
            storage.create_ml_predictions_table(conn)
            logger.info("✓ Tabelas verificadas/criadas com sucesso")
        except Exception as e:
            logger.error(f"Erro ao criar tabelas: {e}")
            return
        finally:
            conn.close()
    else:
        logger.error("Falha ao conectar ao banco de dados. Abortando sincronização.")
        return
    
    # ===== PHASE 1: DATA COLLECTION =====
    logger.info(f"📡 Coletando dados de mercado para {DEFAULT_SYMBOL} ({DEFAULT_INTERVAL})...")
    
    # 1. Collect Klines with pagination
    start_ts_klines = storage.get_start_timestamp_for_collection(
        storage.get_last_timestamp_from_db, klines_table_name, DEFAULT_HISTORICAL_DAYS
    )
    end_ts_klines = int(datetime.now().timestamp() * 1000)
    
    start_date = datetime.fromtimestamp(start_ts_klines / 1000)
    end_date = datetime.fromtimestamp(end_ts_klines / 1000)
    logger.info(f"  📈 Klines: {start_date.strftime('%Y-%m-%d %H:%M:%S')} até {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if start_ts_klines < end_ts_klines:
        klines_df = sources.fetch_all_klines(
            DEFAULT_SYMBOL, DEFAULT_INTERVAL, start_ts_klines, end_ts_klines,
            max_klines_per_request=DEFAULT_KLINES_LIMIT,
            binance_api_base_url=BINANCE_API_BASE_URL
        )
        
        if klines_df is None:
            logger.warning("  ⚠️  API de klines retornou None - usando dados existentes do banco")
        elif not klines_df.empty:
            logger.info(f"  ✓ Coletadas {len(klines_df)} klines com sucesso")
            storage.save_klines_to_db(klines_df, klines_table_name)
            logger.info(f"  ✓ Klines salvas no banco de dados")
        else:
            logger.warning("  ⚠️  Nenhuma kline nova coletada - usando dados existentes")
    else:
        logger.info("  ✓ Klines já estão atualizadas")
    
    # 2. Collect Fear & Greed
    logger.info("  😨 Coletando Fear & Greed Index...")
    start_ts_fng_sec = storage.get_start_timestamp_for_collection(
        storage.get_last_fng_timestamp_from_db, fng_table_name, DEFAULT_HISTORICAL_DAYS
    )
    fng_data = sources.get_fear_and_greed_index(
        limit=DEFAULT_HISTORICAL_DAYS, start_date_unix_sec=start_ts_fng_sec, fng_api_url=FNG_API_URL
    )
    if fng_data:
        storage.save_fng_to_db(fng_data, fng_table_name)
        logger.info("  ✓ Fear & Greed Index atualizado")
    else:
        logger.warning("  ⚠️  Falha ao coletar Fear & Greed Index")
    
    # 3. Collect On-Chain (Blockchair)
    logger.info("  ⛓️  Coletando métricas on-chain...")
    on_chain_data = sources.get_bitcoin_network_fees(blockchair_api_url=BLOCKCHAIR_API_URL)
    if on_chain_data:
        storage.save_on_chain_to_db(on_chain_data, on_chain_table_name)
        logger.info("  ✓ Métricas on-chain atualizadas")
    else:
        logger.warning("  ⚠️  Falha ao coletar métricas on-chain")
    
    # 4. Collect Funding Rate
    logger.info("  💰 Coletando Funding Rate...")
    start_ts_funding = storage.get_start_timestamp_for_collection(
        storage.get_last_funding_rate_timestamp_from_db, funding_rate_table_name, DEFAULT_HISTORICAL_DAYS
    )
    end_ts_funding = int(datetime.now().timestamp() * 1000)
    
    try:
        funding_data = sources.get_funding_rate_history(
            DEFAULT_SYMBOL, limit=1000, start_time_ms=start_ts_funding, end_time_ms=end_ts_funding,
            binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL
        )
        if funding_data:
            storage.save_funding_rate_to_db(funding_data, funding_rate_table_name)
            logger.info("  ✓ Funding Rate atualizado")
        else:
            logger.warning("  ⚠️  Nenhum dado de Funding Rate coletado")
    except Exception as e:
        logger.warning(f"  ⚠️  Falha ao coletar Funding Rate: {e}")

    # 5. Collect Open Interest
    logger.info("  📊 Coletando Open Interest...")
    start_ts_oi = storage.get_start_timestamp_for_collection(
        storage.get_last_open_interest_timestamp_from_db, open_interest_table_name, DEFAULT_HISTORICAL_DAYS
    )
    end_ts_oi = int(datetime.now().timestamp() * 1000)
    
    try:
        oi_data = sources.get_open_interest_history(
            DEFAULT_SYMBOL, period=DEFAULT_INTERVAL, limit=500, 
            start_time_ms=start_ts_oi, end_time_ms=end_ts_oi,
            binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL
        )
        if oi_data:
            storage.save_open_interest_to_db(oi_data, open_interest_table_name)
            logger.info("  ✓ Open Interest atualizado")
        else:
            logger.warning("  ⚠️  Nenhum dado de Open Interest coletado")
    except Exception as e:
        logger.warning(f"  ⚠️  Falha ao coletar Open Interest: {e}")
    
    # 6. Collect Implied Volatility (Deribit)
    logger.info("  📉 Coletando Implied Volatility...")
    start_ts_iv = storage.get_start_timestamp_for_collection(
        storage.get_last_implied_volatility_timestamp_from_db, implied_vol_table_name, DEFAULT_HISTORICAL_DAYS
    )
    iv_data = sources.get_implied_volatility_history(start_timestamp_ms=start_ts_iv, deribit_base_url=DERIBIT_API_BASE_URL)
    if iv_data:
        storage.save_implied_volatility_to_db(iv_data, implied_vol_table_name)
        logger.info("  ✓ Implied Volatility atualizada")
    else:
        logger.warning("  ⚠️  Falha ao coletar Implied Volatility")
    
    # 7. Collect Uniswap Pool Data
    logger.info("  🦄 Coletando dados do pool Uniswap...")
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
        logger.info("  ✓ Dados do pool Uniswap atualizados")
    else:
        logger.warning("  ⚠️  Falha ao coletar dados do pool Uniswap")
    
    logger.info("=" * 80)
    logger.info("✅ SINCRONIZAÇÃO DE DADOS DE MERCADO CONCLUÍDA COM SUCESSO!")
    logger.info("=" * 80)


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
        
        # Guard clause: handle None or empty response from API
        if klines_df is None:
            logger.error("API returned None - connection failed. Will try to load from database.")
            klines_df = pd.DataFrame()
        elif not klines_df.empty:
            logger.info(f"✓ Collected {len(klines_df)} klines successfully")
            storage.save_klines_to_db(klines_df, klines_table_name)
            logger.info(f"✓ Klines saved to database (table: {klines_table_name})")
        else:
            logger.warning("No klines collected (empty DataFrame) - will try to load from database.")
    else:
        logger.warning("No new klines collected (invalid timestamps) - will try to load from database.")
    
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
    
    # 4. Collect Funding Rate (with date range support for retroactive collection)
    # Binance Futures Funding Rate started 2019-06-01; anything before returns empty but doesn't crash
    start_ts_funding = storage.get_start_timestamp_for_collection(
        storage.get_last_funding_rate_timestamp_from_db, funding_rate_table_name, DEFAULT_HISTORICAL_DAYS
    )
    end_ts_funding = int(datetime.now().timestamp() * 1000)
    
    try:
        funding_data = sources.get_funding_rate_history(
            DEFAULT_SYMBOL, limit=1000, start_time_ms=start_ts_funding, end_time_ms=end_ts_funding,
            binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL
        )
        if funding_data:
            storage.save_funding_rate_to_db(funding_data, funding_rate_table_name)
    except Exception as e:
        logger.warning(f"  ⚠️  Falha ao coletar Funding Rate: {e}")
    
    # 5. Collect Open Interest
    start_ts_oi = storage.get_start_timestamp_for_collection(
        storage.get_last_open_interest_timestamp_from_db, open_interest_table_name, DEFAULT_HISTORICAL_DAYS
    )
    end_ts_oi = int(datetime.now().timestamp() * 1000)
    
    try:
        oi_data = sources.get_open_interest_history(
            DEFAULT_SYMBOL, period=DEFAULT_INTERVAL, limit=500, 
            start_time_ms=start_ts_oi, end_time_ms=end_ts_oi,
            binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL
        )
        if oi_data:
            storage.save_open_interest_to_db(oi_data, open_interest_table_name)
    except Exception as e:
        logger.warning(f"  ⚠️  Falha ao coletar Open Interest: {e}")
    
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
    
    # Guard clause: ensure we have a valid DataFrame
    if all_klines_df is None:
        logger.error("Failed to load data from database (returned None).")
        return pd.DataFrame()
    
    if all_klines_df.empty:
        logger.error("No sufficient data in database to continue. Please check data collection.")
        return pd.DataFrame()
    
    logger.info(f"Klines DataFrame loaded with {len(all_klines_df)} klines for calculation.")
    
    # Calculate minimal indicator set (feature selection)
    try:
        # 1. Momentum
        all_klines_df['RSI'] = indicators.calculate_rsi(all_klines_df, column='Close', window=14)

        # 2. Trend (EMA50 distance)
        all_klines_df['EMA_50'] = indicators.calculate_ema(all_klines_df, column='Close', window=50)
        all_klines_df['SMA_200'] = indicators.calculate_sma(all_klines_df, column='Close', window=200)

        # 3. Volatility (Bollinger Band Width)
        bb_df = indicators.calculate_bollinger_bands(all_klines_df, column='Close', window=20)
        
        # Guard clause: check if bb_df is valid
        if bb_df is None or bb_df.empty:
            logger.error("Bollinger Bands calculation returned None or empty DataFrame.")
            return pd.DataFrame()
            
        all_klines_df['BB_Middle'] = bb_df['BB_Middle']
        all_klines_df['BB_Upper'] = bb_df['BB_Upper']
        all_klines_df['BB_Lower'] = bb_df['BB_Lower']
        bb_middle_safe = all_klines_df['BB_Middle'].replace(0, np.nan)
        all_klines_df['BB_Width'] = (all_klines_df['BB_Upper'] - all_klines_df['BB_Lower']) / bb_middle_safe
        
    except Exception as e:
        logger.error(f"Failed to calculate technical indicators: {e}")
        return pd.DataFrame()
    
    # ===== PHASE 3: MERGE AUXILIARY DATA SOURCES =====
    # Load auxiliary data
    conn = storage.create_connection()
    if not conn:
        logger.error("Failed to connect to database for auxiliary data")
        return pd.DataFrame()
    
    try:
        funding_rate_df = pd.read_sql(f"SELECT funding_time, funding_rate FROM {funding_rate_table_name}", conn)
        open_interest_df = pd.read_sql(f"SELECT timestamp, open_interest FROM {open_interest_table_name}", conn)
        
        # Guard clauses: ensure valid DataFrames
        if funding_rate_df is None:
            funding_rate_df = pd.DataFrame()
        if open_interest_df is None:
            open_interest_df = pd.DataFrame()
            
    except Exception as e:
        logger.warning(f"Failed to load funding/OI data: {e}")
        funding_rate_df = pd.DataFrame()
        open_interest_df = pd.DataFrame()
    finally:
        conn.close()
    
    uniswap_df = storage.get_uniswap_pool_data_from_db(uniswap_table_name)
    
    # Guard clause: ensure uniswap_df is valid
    if uniswap_df is None:
        logger.warning("Uniswap data returned None. Using empty DataFrame.")
        uniswap_df = pd.DataFrame()
    
    # Merge Sentiment (Funding + OI)
    if not funding_rate_df.empty and not open_interest_df.empty:
        try:
            funding_rate_df['Timestamp'] = pd.to_datetime(funding_rate_df['funding_time'], unit='ms')
            open_interest_df['Timestamp'] = pd.to_datetime(open_interest_df['timestamp'], unit='ms')
            
            sentiment_data_df = pd.merge(
                funding_rate_df[['Timestamp', 'funding_rate']], 
                open_interest_df[['Timestamp', 'open_interest']], 
                on='Timestamp', how='outer'
            ).sort_values(by='Timestamp').ffill().dropna()
            
            # Guard clause: ensure sentiment_data_df is valid
            if sentiment_data_df is None:
                logger.warning("Sentiment data merge returned None. Skipping sentiment merge.")
                sentiment_data_df = pd.DataFrame()
            
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
                    
        except Exception as e:
            logger.warning(f"Failed to merge sentiment data: {e}. Filling FundingRate/OpenInterest with 0.")
            all_klines_df['FundingRate'] = 0.0
            all_klines_df['OpenInterest'] = 0.0
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
        all_klines_df['dist_from_sma_200'] = (all_klines_df['Close'] - all_klines_df['SMA_200']) / all_klines_df['SMA_200']

        all_klines_df['oi_change_4h'] = all_klines_df['OpenInterest'].pct_change().fillna(0.0)
        # Avoid infinity if OpenInterest was 0
        all_klines_df['oi_change_4h'] = all_klines_df['oi_change_4h'].replace([np.inf, -np.inf], 0.0)
        
        all_klines_df['funding_velocity'] = all_klines_df['FundingRate'].diff().fillna(0.0)

        # --- APLICAR SHIFT(1) NAS FEATURES (ZERO LOOK-AHEAD BIAS) ---
        # Definir as colunas que são features para o modelo
        feature_cols = [
            'RSI', 'dist_from_ema_50', 'dist_from_sma_200', 'BB_Width',
            'FundingRate', 'OpenInterest', 'VolumeUSD', 'oi_change_4h', 'funding_velocity'
        ]
        
        # Aplicar o shift(1) apenas nas features existentes no DataFrame
        cols_to_shift = [col for col in feature_cols if col in all_klines_df.columns]
        logger.info(f"Aplicando shift(1) em {len(cols_to_shift)} colunas de features para evitar Look-ahead Bias.")
        all_klines_df[cols_to_shift] = all_klines_df[cols_to_shift].shift(1)

        # 2. Create Target (trend over next candles)
        future_close = all_klines_df['Close'].shift(-ML_PREDICTION_HORIZON)
        log_return = np.log(future_close / all_klines_df['Close'])
        all_klines_df['Target_Trend'] = (log_return > ML_TARGET_MIN_CHANGE).astype(int)

        # 3. Clean data
        REQUIRED_COLUMNS = feature_cols + ['Target_Trend']
        
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
        
        # Guard clause: ensure df is valid
        if df is None:
            logger.warning("pd.read_sql returned None for positions_log.")
            return pd.DataFrame()
        
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
        
        # Guard clause: ensure df is valid
        if df is None:
            logger.warning("pd.read_sql returned None for ml_predictions.")
            return pd.DataFrame()
        
        if not df.empty:
            # open_time is already a TIMESTAMP in the database, pd.read_sql will convert it to datetime automatically
            if not pd.api.types.is_datetime64_any_dtype(df['open_time']):
                df['open_time'] = pd.to_datetime(df['open_time'])
        
        return df
    
    except Exception as e:
        logger.warning(f"Error reading 'ml_predictions' from DB: {e}. Table may not exist.")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

            conn.close()
