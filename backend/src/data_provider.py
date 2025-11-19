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

from .config import (
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

# Constantes do Modelo de ML
PREDICTION_HORIZON_DAYS = 7 # 7 dias
PREDICTION_FALL_THRESHOLD = -0.03  # -3%


logger = logging.getLogger(__name__)


def get_full_prepared_data():
    """
    Orquestra as Fases 1, 2, 3 e 4: coleta, persistencia, calculo de indicadores,
    merge de dados e preparação para ML.
    """
    
    # --- CORREÇÃO: Definição dos nomes das tabelas ---
    klines_table_name = f"{DEFAULT_SYMBOL}_{DEFAULT_INTERVAL}_klines"
    fng_table_name = "fear_and_greed_index"
    on_chain_table_name = "bitcoin_on_chain_metrics"
    funding_rate_table_name = "binance_futures_funding_rate"
    open_interest_table_name = "binance_futures_open_interest"
    implied_vol_table_name = "implied_volatility"
    uniswap_table_name = "uniswap_pool_data"
    
    # --- FASE 1: VERIFICAR TABELAS E COLETAR DADOS ---
    logger.info("Verificando a existencia das tabelas no banco de dados...")
    conn_check = create_connection(DB_FILE)
    if conn_check:
        create_implied_volatility_table(conn_check, implied_vol_table_name)
        create_uniswap_pool_table(conn_check, uniswap_table_name)
        conn_check.close()
        
    logger.info(f"Iniciando processo de coleta/preparacao para {DEFAULT_SYMBOL} ({DEFAULT_INTERVAL})...")
    
    # 1. Coletar Velas (Klines)
    start_ts_klines = get_start_timestamp_for_collection(get_last_timestamp_from_db, klines_table_name, DB_FILE, DEFAULT_HISTORICAL_DAYS)
    end_ts_klines = int(datetime.now().timestamp() * 1000)
    
    if start_ts_klines < end_ts_klines:
        klines_df = fetch_all_klines(
            DEFAULT_SYMBOL, DEFAULT_INTERVAL, start_ts_klines, end_ts_klines,
            binance_api_base_url=BINANCE_API_BASE_URL
        )
        if not klines_df.empty:
            save_klines_to_db(klines_df, klines_table_name, DB_FILE)
    else:
        logger.warning("Nenhuma nova vela foi coletada.")

    # 2. Coletar Fear & Greed
    start_ts_fng_sec = get_start_timestamp_for_collection(get_last_fng_timestamp_from_db, fng_table_name, DB_FILE, DEFAULT_HISTORICAL_DAYS)
    fng_data = get_fear_and_greed_index(limit=DEFAULT_HISTORICAL_DAYS, start_date_unix_sec=start_ts_fng_sec, fng_api_url=FNG_API_URL)
    if fng_data:
        save_fng_to_db(fng_data, fng_table_name, DB_FILE)

    # 3. Coletar On-Chain (Blockchair) - (Executa apenas uma vez por dia, aproximadamente)
    on_chain_data = get_bitcoin_network_fees(blockchair_api_url=BLOCKCHAIR_API_URL)
    if on_chain_data:
        save_on_chain_to_db(on_chain_data, on_chain_table_name, DB_FILE)

    # 4. Coletar Funding Rate (Binance Futures)
    funding_data = get_funding_rate_history(DEFAULT_SYMBOL, limit=100, binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL)
    if funding_data:
        save_funding_rate_to_db(funding_data, funding_rate_table_name, DB_FILE)

    # 5. Coletar Open Interest (Binance Futures)
    oi_data = get_open_interest(DEFAULT_SYMBOL, binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL)
    if oi_data:
        save_open_interest_to_db(oi_data, open_interest_table_name, DB_FILE)

    # 6. Coletar Implied Volatility (Deribit)
    start_ts_iv = get_start_timestamp_for_collection(get_last_implied_volatility_timestamp_from_db, implied_vol_table_name, DB_FILE, DEFAULT_HISTORICAL_DAYS)
    iv_data = get_implied_volatility_history(start_timestamp_ms=start_ts_iv, deribit_base_url=DERIBIT_API_BASE_URL)
    if iv_data:
        save_implied_volatility_to_db(iv_data, implied_vol_table_name, DB_FILE)

    # 7. Coletar Uniswap Pool Data (The Graph)
    start_ts_uni = get_start_timestamp_for_collection(get_last_uniswap_timestamp_from_db, uniswap_table_name, DB_FILE, DEFAULT_HISTORICAL_DAYS)
    uni_data = get_uniswap_pool_daily_data(
        pool_id=DEFAULT_POLYGON_POOL_ID,
        start_timestamp_ms=start_ts_uni,
        thegraph_base_url=THEGRAPH_UNISWAP_V3_URL,
        thegraph_api_key=THEGRAPH_API_KEY,
        thegraph_subgraph_ids=THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS,
        default_network=DEFAULT_NETWORK
    )
    if uni_data:
        save_uniswap_pool_data_to_db(uni_data, uniswap_table_name, DB_FILE)
    
    # --- FASE 2: CARREGAMENTO DE DADOS E CALCULO DE INDICADORES ---
    all_klines_df = get_data_from_db(klines_table_name, DB_FILE)
    if all_klines_df.empty:
        logger.warning("Nao ha dados suficientes no banco de dados para continuar.")
        return pd.DataFrame()

    logger.info("DataFrame de velas carregado com %d velas para calculo.", len(all_klines_df))
    
    # --- CORREÇÃO: Calcular TODOS os indicadores que o ML precisa ---
    all_klines_df['SMA_20'] = calculate_sma(all_klines_df, column='Close', window=20)
    all_klines_df['SMA_50'] = calculate_sma(all_klines_df, column='Close', window=50)
    all_klines_df['EMA_20'] = calculate_ema(all_klines_df, column='Close', window=20)
    all_klines_df['RSI'] = calculate_rsi(all_klines_df, column='Close', window=14)
    all_klines_df['ATR'] = calculate_atr(all_klines_df, window=14)
    # (Adicione outros aqui se necessário)

    # --- FASE 3: CALCULO DE INDICADORES COMPOSTOS (merge de fontes auxiliares) ---
    conn = create_connection(DB_FILE)
    funding_rate_df = pd.read_sql("SELECT FundingTime, FundingRate FROM " + funding_rate_table_name, conn)
    open_interest_df = pd.read_sql("SELECT Timestamp, OpenInterest FROM " + open_interest_table_name, conn)
    fng_df = get_fng_data_from_db(fng_table_name, DB_FILE)
    iv_df = get_implied_volatility_data_from_db(implied_vol_table_name, DB_FILE)
    uniswap_df = get_uniswap_pool_data_from_db(uniswap_table_name, DB_FILE)
    conn.close()

    # Merge Sentimento (Funding + OI)
    if not funding_rate_df.empty and not open_interest_df.empty:
        funding_rate_df['Timestamp'] = pd.to_datetime(funding_rate_df['FundingTime'], unit='ms')
        open_interest_df['Timestamp'] = pd.to_datetime(open_interest_df['Timestamp'], unit='ms')
        sentiment_data_df = pd.merge(funding_rate_df[['Timestamp', 'FundingRate']], open_interest_df[['Timestamp', 'OpenInterest']], on='Timestamp', how='outer').sort_values(by='Timestamp').ffill().dropna()
        if not sentiment_data_df.empty:
            sentiment_data_df['Sentimento_Score'] = calculate_composite_sentiment(sentiment_data_df['FundingRate'], sentiment_data_df['OpenInterest'])
            all_klines_df['Date'] = all_klines_df['Open_time'].dt.date
            sentiment_data_df['Date'] = sentiment_data_df['Timestamp'].dt.date
            daily_sentiment = sentiment_data_df.groupby('Date').last().reset_index()
            cols_to_merge = ['Date', 'Sentimento_Score', 'FundingRate', 'OpenInterest']
            all_klines_df = pd.merge(all_klines_df, daily_sentiment[cols_to_merge], on='Date', how='left')
            
            # Preencher vazios
            all_klines_df['FundingRate'] = all_klines_df['FundingRate'].ffill().bfill()
            all_klines_df['OpenInterest'] = all_klines_df['OpenInterest'].ffill().bfill()
            all_klines_df['Sentimento_Score'] = all_klines_df['Sentimento_Score'].ffill().bfill()
            if 'Date' in all_klines_df.columns:
                 all_klines_df.drop(columns=['Date'], inplace=True)

    # Merge FNG_Value (Fear & Greed)
    if not fng_df.empty:
        fng_df['Date'] = fng_df['Timestamp'].dt.date
        daily_fng = fng_df.groupby('Date').last().reset_index()[['Date', 'Value']]
        daily_fng.rename(columns={'Value': 'FNG_Value'}, inplace=True)
        
        all_klines_df['Date'] = all_klines_df['Open_time'].dt.date
        all_klines_df = pd.merge(all_klines_df, daily_fng, on='Date', how='left')
        
        all_klines_df['FNG_Value'] = all_klines_df['FNG_Value'].ffill()
        all_klines_df['FNG_Value'] = all_klines_df['FNG_Value'].bfill()
        
        if 'Date' in all_klines_df.columns:
            all_klines_df.drop(columns=['Date'], inplace=True)
    else:
        logger.warning("Nenhum dado de F&G disponivel; 'FNG_Value' será neutro (50).")
        all_klines_df['FNG_Value'] = 50.0

    # Merge Implied Volatility
    if not iv_df.empty:
        iv_df['Date'] = iv_df['Timestamp'].dt.date
        daily_iv = iv_df.groupby('Date').last().reset_index()[['Date', 'Volatility']]
        daily_iv.rename(columns={'Volatility': 'Implied_Volatility'}, inplace=True)
        all_klines_df['Date'] = all_klines_df['Open_time'].dt.date
        all_klines_df = pd.merge(all_klines_df, daily_iv, on='Date', how='left')
        all_klines_df['Implied_Volatility'] = all_klines_df['Implied_Volatility'].ffill().bfill()
        if 'Date' in all_klines_df.columns:
            all_klines_df.drop(columns=['Date'], inplace=True)
    else:
        logger.warning("Nenhum dado de Implied Volatility disponivel; Volatilidade sera baseada em fallback (ATR).")

    # Merge Uniswap Pool Data
    if not uniswap_df.empty:
        uniswap_df['Date'] = uniswap_df['Timestamp'].dt.date
        daily_uniswap = uniswap_df.groupby('Date').last().reset_index()[['Date', 'VolumeUSD', 'TVL_USD']]
        all_klines_df['Date'] = all_klines_df['Open_time'].dt.date
        all_klines_df = pd.merge(all_klines_df, daily_uniswap, on='Date', how='left')
        all_klines_df['VolumeUSD'] = all_klines_df['VolumeUSD'].ffill().bfill()
        all_klines_df['TVL_USD'] = all_klines_df['TVL_USD'].ffill().bfill()
        if 'Date' in all_klines_df.columns:
            all_klines_df.drop(columns=['Date'], inplace=True)
    else:
        logger.warning("Nenhum dado Uniswap disponivel; Oportunidade sera baseada em fallback (on-exchange volume).")

    # Garante que os scores sejam calculados e nao contenham NaN
    # (Este bloco precisa vir DEPOIS dos merges)
    try:
        all_klines_df['Volatilidade_Score'] = calculate_composite_volatility(all_klines_df, iv_col='Implied_Volatility', atr_col='ATR')
        all_klines_df['Oportunidade_Score'] = calculate_composite_opportunity(all_klines_df, volume_onchain_col='VolumeUSD', tvl_col='TVL_USD')
    except Exception as e:
        logger.warning(f"Nao foi possivel calcular scores compostos: {e}. Usando fallback.")
        all_klines_df['Volatilidade_Score'] = 0.5
        all_klines_df['Oportunidade_Score'] = 0.5
        
    if 'Sentimento_Score' not in all_klines_df.columns:
        logger.warning("Aviso: Score de Sentimento nao pode ser calculado...")
        all_klines_df['Sentimento_Score'] = 0.5
        
    all_klines_df.fillna({
        'Sentimento_Score': 0.5,
        'Volatilidade_Score': 0.5,
        'Oportunidade_Score': 0.5
    }, inplace=True)
    
    
    # --- FASE 4 - PREPARAÇÃO DE DADOS PARA ML ---
    try:
        # 1. Criar Features Adicionais (Feature Engineering)
        all_klines_df['dist_from_sma_50'] = (all_klines_df['Close'] - all_klines_df['SMA_50']) / all_klines_df['SMA_50']

        # 2. Criar a coluna "Alvo" (Target)
        future_price = all_klines_df['Close'].shift(-PREDICTION_HORIZON_DAYS)
        percent_change = (future_price - all_klines_df['Close']) / all_klines_df['Close']
        all_klines_df['target_price_fell'] = (percent_change <= PREDICTION_FALL_THRESHOLD).astype(int)
        
        # 3. Garantir que FNG_Value existe (do merge da FASE 3)
        if 'FNG_Value' not in all_klines_df.columns:
            logger.warning("Coluna 'FNG_Value' não encontrada (após merge). Preenchendo com 50.")
            all_klines_df['FNG_Value'] = 50.0

        # 4. Limpar dados
        COLUNAS_NECESSARIAS = [
            'SMA_50', 'RSI', 'FNG_Value', 'dist_from_sma_50', 'target_price_fell',
            'Implied_Volatility', 'FundingRate', 'OpenInterest', 'VolumeUSD'
        ]
        
        all_klines_df = all_klines_df.dropna(subset=COLUNAS_NECESSARIAS)
        logger.info(f"Colunas de Feature e Alvo criadas. Total de {len(all_klines_df)} amostras de treinamento prontas.")

    except Exception as e:
        logger.error(f"Falha ao criar features/alvo para o modelo de ML: {e}")
        return pd.DataFrame() 

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

def get_predictions_from_db(db_file: str = DB_FILE) -> pd.DataFrame:
    """
    Carrega as predições de ML (timestamp, prediction, prediction_correct) do DB.
    """
    conn = create_connection(db_file)
    if not conn:
        return pd.DataFrame()
        
    try:
        base_query = "SELECT * FROM ml_predictions ORDER BY Open_time ASC"
        df = pd.read_sql(base_query, conn)
        
        if not df.empty:
            df['Open_time'] = pd.to_datetime(df['Open_time'], unit='ms')
        return df
        
    except Exception as e:
        logger.warning(f"Erro ao ler 'ml_predictions' do DB: {e}. A tabela pode não existir.")
        return pd.DataFrame() 
    finally:
        if conn:
            conn.close()

