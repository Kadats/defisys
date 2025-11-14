import time
import pandas as pd
from datetime import datetime, timedelta
import logging

# Importa as funcoes existentes
from defi_data_toolkit.data_collector import (
    fetch_all_klines, get_fear_and_greed_index, get_bitcoin_network_fees,
    get_funding_rate_history, get_open_interest, get_uniswap_pool_daily_data,
    get_implied_volatility_history
)

from defi_data_toolkit.database import (
    create_connection, get_last_timestamp_from_db, save_klines_to_db, get_data_from_db,
    save_fng_to_db, get_last_fng_timestamp_from_db, get_fng_data_from_db,
    save_on_chain_to_db, save_funding_rate_to_db, save_open_interest_to_db,
    get_start_timestamp_for_collection, save_implied_volatility_to_db, get_implied_volatility_data_from_db,
    get_last_implied_volatility_timestamp_from_db, save_uniswap_pool_data_to_db, get_uniswap_pool_data_from_db, get_last_uniswap_timestamp_from_db,
    create_implied_volatility_table, create_uniswap_pool_table
)

from defi_data_toolkit.indicators import (
    calculate_sma, calculate_ema, calculate_rsi, calculate_macd,
    calculate_bollinger_bands, calculate_stochastic_oscillator,
    calculate_obv, calculate_atr, calculate_fibonacci_retracements,
    calculate_composite_sentiment, calculate_composite_volatility, 
    calculate_composite_opportunity
)

from config import (
    DB_FILE,
    DEFAULT_SYMBOL,
    DEFAULT_INTERVAL,
    DEFAULT_HISTORICAL_DAYS,
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


def get_full_prepared_data():
    """
    Orquestra as Fases 1, 2 e 3: coleta, persistencia, calculo de indicadores e merge de dados auxiliares.

    Retorna:
        pd.DataFrame: all_klines_df pronto para rodar o backtest.
    """
    # Definicao dos nomes das tabelas
    klines_table_name = f"{DEFAULT_SYMBOL}_{DEFAULT_INTERVAL}_klines"
    fng_table_name = "fear_and_greed_index"
    on_chain_table_name = "bitcoin_on_chain_metrics"
    funding_rate_table_name = "binance_futures_funding_rate"
    open_interest_table_name = "binance_futures_open_interest"
    implied_vol_table_name = "implied_volatility"
    uniswap_table_name = "uniswap_pool_data"

    # Garantir que todas as tabelas auxiliares existam antes de qualquer leitura/escrita
    logger.info("Verificando a existencia das tabelas no banco de dados...")
    with create_connection(DB_FILE) as conn:
        if conn:
            create_implied_volatility_table(conn, implied_vol_table_name)
            create_uniswap_pool_table(conn, uniswap_table_name)

    logger.info("Iniciando processo de coleta/preparacao para %s (%s)...", DEFAULT_SYMBOL, DEFAULT_INTERVAL)

    # --- FASE 1: COLETA DE DADOS E ATUALIZACAO DO BANCO DE DADOS ---
    start_time_ms_klines = get_start_timestamp_for_collection(get_last_timestamp_from_db, klines_table_name, DB_FILE, DEFAULT_HISTORICAL_DAYS)
    df_klines_new = fetch_all_klines(
        DEFAULT_SYMBOL,
        DEFAULT_INTERVAL,
        start_time_ms_klines,
        int(time.time() * 1000),
        binance_api_base_url=BINANCE_API_BASE_URL,
    )
    if not df_klines_new.empty:
        logger.info("Total de %d novas velas coletadas.", len(df_klines_new))
        save_klines_to_db(df_klines_new, klines_table_name, DB_FILE)
    else:
        logger.warning("Nenhuma nova vela foi coletada.")

    # FNG
    last_timestamp_fng_sec = get_last_fng_timestamp_from_db(fng_table_name, DB_FILE)
    fng_data_new = (
        get_fear_and_greed_index(limit=365, fng_api_url=FNG_API_URL)
        if not last_timestamp_fng_sec
        else get_fear_and_greed_index(limit=365, start_date_unix_sec=last_timestamp_fng_sec, fng_api_url=FNG_API_URL)
    )
    if fng_data_new:
        save_fng_to_db(fng_data_new, fng_table_name, DB_FILE)

    # On-chain
    on_chain_data = get_bitcoin_network_fees(blockchair_api_url=BLOCKCHAIR_API_URL)
    if on_chain_data:
        save_on_chain_to_db(on_chain_data, on_chain_table_name, DB_FILE)

    # Funding Rate
    funding_rate_data = get_funding_rate_history(symbol=DEFAULT_SYMBOL, binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL)
    if funding_rate_data:
        save_funding_rate_to_db(funding_rate_data, funding_rate_table_name, DB_FILE)

    # Open Interest
    open_interest_data = get_open_interest(symbol=DEFAULT_SYMBOL, binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL)
    if open_interest_data:
        save_open_interest_to_db(open_interest_data, open_interest_table_name, DB_FILE)

    # Implied Volatility
    start_ts_iv = get_start_timestamp_for_collection(get_last_implied_volatility_timestamp_from_db, implied_vol_table_name, DB_FILE, DEFAULT_HISTORICAL_DAYS)
    iv_data = get_implied_volatility_history(
        index_name="BTC_DVOL",
        resolution="1D",
        start_timestamp_ms=start_ts_iv,
        end_timestamp_ms=int(time.time() * 1000),
        limit=1000,
        deribit_base_url=DERIBIT_API_BASE_URL,
    )
    if iv_data:
        save_implied_volatility_to_db(iv_data, implied_vol_table_name, DB_FILE)

    # Uniswap V3 pool daily data
    start_ts_uniswap = get_start_timestamp_for_collection(get_last_uniswap_timestamp_from_db, uniswap_table_name, DB_FILE, DEFAULT_HISTORICAL_DAYS)
    uniswap_data = get_uniswap_pool_daily_data(
        pool_id=DEFAULT_POLYGON_POOL_ID,
        start_timestamp_ms=start_ts_uniswap,
        end_timestamp_ms=int(time.time() * 1000),
        limit=1000,
        thegraph_base_url=THEGRAPH_UNISWAP_V3_URL,
        thegraph_api_key=THEGRAPH_API_KEY,
        thegraph_subgraph_ids=THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS,
        default_network=DEFAULT_NETWORK,
    )
    if uniswap_data:
        save_uniswap_pool_data_to_db(uniswap_data, uniswap_table_name, DB_FILE)

    # --- FASE 2: CARREGAMENTO DE DADOS E CALCULO DE INDICADORES ---
    all_klines_df = get_data_from_db(klines_table_name, DB_FILE)
    if all_klines_df.empty:
        logger.warning("Nao ha dados suficientes no banco de dados para continuar.")
        return pd.DataFrame()

    logger.info("DataFrame de velas carregado com %d velas para calculo.", len(all_klines_df))

    # Adicionar Volume On-Chain como proxy do volume de klines
    all_klines_df['Vol_onchain'] = all_klines_df['Volume']

    # Calcular Indicadores Tecnicos
    all_klines_df['SMA_20'] = calculate_sma(all_klines_df, column='Close', window=20)
    all_klines_df['SMA_50'] = calculate_sma(all_klines_df, column='Close', window=50)
    all_klines_df['EMA_20'] = calculate_ema(all_klines_df, column='Close', window=20)
    all_klines_df['RSI'] = calculate_rsi(all_klines_df, column='Close', window=14)
    macd_df = calculate_macd(all_klines_df, column='Close')
    all_klines_df = pd.concat([all_klines_df, macd_df], axis=1)
    bb_df = calculate_bollinger_bands(all_klines_df, column='Close')
    all_klines_df = pd.concat([all_klines_df, bb_df], axis=1)
    stoch_df = calculate_stochastic_oscillator(all_klines_df, high_col='High', low_col='Low', close_col='Close', k_window=14, d_window=3)
    all_klines_df = pd.concat([all_klines_df, stoch_df], axis=1)
    all_klines_df['OBV'] = calculate_obv(all_klines_df, close_col='Close', volume_col='Volume')
    all_klines_df['ATR'] = calculate_atr(all_klines_df, high_col='High', low_col='Low', close_col='Close', window=14)
    fib_df = calculate_fibonacci_retracements(all_klines_df, high_col='High', low_col='Low', window=60)
    all_klines_df = pd.concat([all_klines_df, fib_df], axis=1)

    # --- FASE 3: CALCULO DE INDICADORES COMPOSTOS (merge de fontes auxiliares) ---
    conn = create_connection(DB_FILE)
    funding_rate_df = pd.read_sql("SELECT FundingTime, FundingRate FROM " + funding_rate_table_name, conn)
    open_interest_df = pd.read_sql("SELECT Timestamp, OpenInterest FROM " + open_interest_table_name, conn)
    conn.close()

    if not funding_rate_df.empty and not open_interest_df.empty:
        funding_rate_df['Timestamp'] = pd.to_datetime(funding_rate_df['FundingTime'], unit='ms')
        open_interest_df['Timestamp'] = pd.to_datetime(open_interest_df['Timestamp'], unit='ms')

        sentiment_data_df = pd.merge(
            funding_rate_df[['Timestamp', 'FundingRate']],
            open_interest_df[['Timestamp', 'OpenInterest']],
            on='Timestamp',
            how='outer'
        ).sort_values(by='Timestamp').ffill().dropna()

        if not sentiment_data_df.empty:
            sentiment_data_df['Sentimento_Score'] = calculate_composite_sentiment(
                sentiment_data_df['FundingRate'],
                sentiment_data_df['OpenInterest']
            )
            
            all_klines_df['Date'] = all_klines_df['Open_time'].dt.date
            sentiment_data_df['Date'] = sentiment_data_df['Timestamp'].dt.date
            
            daily_sentiment = sentiment_data_df.groupby('Date').last().reset_index()

            all_klines_df = pd.merge(
                all_klines_df,
                daily_sentiment[['Date', 'Sentimento_Score']],
                on='Date',
                how='left'
            )
            
            # Preenchimento robusto
            all_klines_df['Sentimento_Score'] = all_klines_df['Sentimento_Score'].ffill()
            all_klines_df['Sentimento_Score'] = all_klines_df['Sentimento_Score'].bfill()
            all_klines_df.drop(columns=['Date'], inplace=True)

    # Merge Implied Volatility
    iv_df = get_implied_volatility_data_from_db(implied_vol_table_name, DB_FILE)
    if not iv_df.empty:
        iv_df['Date'] = iv_df['Timestamp'].dt.date
        daily_iv = iv_df.groupby('Date').last().reset_index()[['Date', 'Volatility']]
        daily_iv.rename(columns={'Volatility': 'Implied_Volatility'}, inplace=True)

        all_klines_df['Date'] = all_klines_df['Open_time'].dt.date
        all_klines_df = pd.merge(all_klines_df, daily_iv, on='Date', how='left')
        all_klines_df['Implied_Volatility'] = all_klines_df['Implied_Volatility'].ffill()
        all_klines_df['Implied_Volatility'] = all_klines_df['Implied_Volatility'].bfill()
        all_klines_df.drop(columns=['Date'], inplace=True)
    else:
        logger.warning("Nenhum dado de Implied Volatility disponivel; Volatilidade sera baseada em fallback (ATR).")

    # Merge Uniswap Pool Data
    uniswap_df = get_uniswap_pool_data_from_db(uniswap_table_name, DB_FILE)
    if not uniswap_df.empty:
        uniswap_df['Date'] = uniswap_df['Timestamp'].dt.date
        daily_uniswap = uniswap_df.groupby('Date').last().reset_index()[['Date', 'VolumeUSD', 'TVL_USD']]

        all_klines_df['Date'] = all_klines_df['Open_time'].dt.date
        all_klines_df = pd.merge(all_klines_df, daily_uniswap, on='Date', how='left')

        all_klines_df['VolumeUSD'] = all_klines_df['VolumeUSD'].ffill().bfill()
        all_klines_df['TVL_USD'] = all_klines_df['TVL_USD'].ffill().bfill()
        all_klines_df.drop(columns=['Date'], inplace=True)
    else:
        logger.warning("Nenhum dado Uniswap disponivel; Oportunidade sera baseada em fallback (on-exchange volume).")

    # Garante que os scores sejam calculados e nao contenham NaN
    if 'Sentimento_Score' in all_klines_df.columns and not all_klines_df['Sentimento_Score'].isnull().all():
        all_klines_df['Volatilidade_Score'] = calculate_composite_volatility(all_klines_df, iv_col='Implied_Volatility', atr_col='ATR')
        all_klines_df['Oportunidade_Score'] = calculate_composite_opportunity(all_klines_df, volume_onchain_col='Vol_onchain')

        all_klines_df[['Sentimento_Score', 'Volatilidade_Score', 'Oportunidade_Score']] = all_klines_df[['Sentimento_Score', 'Volatilidade_Score', 'Oportunidade_Score']].fillna(0.5)
    else:
        logger.warning("Aviso: Score de Sentimento nao pode ser calculado. Scores compostos serao preenchidos com valor neutro.")
        all_klines_df['Sentimento_Score'] = 0.5
        all_klines_df['Volatilidade_Score'] = 0.5
        all_klines_df['Oportunidade_Score'] = 0.5

    return all_klines_df

def get_positions_from_db(db_file: str = DB_FILE, include_open: bool = True, include_closed: bool = True) -> pd.DataFrame:
    """
    Carrega o log de posições (abertas e/ou fechadas) do banco de dados.
    """
    conn = create_connection(db_file)
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
            
        base_query += " ORDER BY open_timestamp DESC" # Mostrar as mais recentes primeiro
            
        df = pd.read_sql(base_query, conn)
        
        if not df.empty:
            df['open_timestamp'] = pd.to_datetime(df['open_timestamp'], unit='ms')
            if 'close_timestamp' in df.columns:
                df['close_timestamp'] = pd.to_datetime(df['close_timestamp'], unit='ms', errors='coerce') # Lida com NaT
        return df
        
    except Exception as e:
        logger.error(f"Erro ao ler 'positions_log' do DB: {e}. A tabela pode não existir ainda.")
        return pd.DataFrame() # Retorna DF vazio se a tabela não existir
    finally:
        if conn:
            conn.close()

