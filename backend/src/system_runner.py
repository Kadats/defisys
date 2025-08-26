import time
import pandas as pd
from datetime import datetime, timedelta

# Importa as funções e configurações dos seus módulos
from .data_collector import (
    fetch_all_klines, get_fear_and_greed_index, get_bitcoin_network_fees,
    get_funding_rate_history, get_open_interest
)
from .database import (
    create_connection, get_last_timestamp_from_db, save_klines_to_db, get_data_from_db,
    save_fng_to_db, get_last_fng_timestamp_from_db, get_fng_data_from_db,
    save_on_chain_to_db, save_funding_rate_to_db, save_open_interest_to_db
)
from .data_collector import get_implied_volatility_history
from .database import save_implied_volatility_to_db, get_implied_volatility_data_from_db, get_last_implied_volatility_timestamp_from_db
from .config import DB_FILE, DEFAULT_SYMBOL, DEFAULT_INTERVAL, DEFAULT_HISTORICAL_DAYS
from .logging_config import setup_logging
import logging

# Modules should obtain a logger instance; actual configuration happens in the entrypoint
logger = logging.getLogger(__name__)

# Importa o módulo de indicadores
from .indicators import (
    calculate_sma, calculate_ema, calculate_rsi, calculate_macd,
    calculate_bollinger_bands, calculate_stochastic_oscillator,
    calculate_obv, calculate_atr, calculate_fibonacci_retracements,
    calculate_composite_sentiment, calculate_composite_volatility, 
    calculate_composite_opportunity
)

# Estratégias
from .strategies import generate_signals, decide_liquidity

# Backtest
from .backtester import run_backtest

def run_trading_system():
    """
    Orquestra a coleta de dados, o cálculo de indicadores, o backtest e a geração de sinais.
    """
    # Definição dos nomes das tabelas
    klines_table_name = f"{DEFAULT_SYMBOL}_{DEFAULT_INTERVAL}_klines"
    fng_table_name = "fear_and_greed_index"
    on_chain_table_name = "bitcoin_on_chain_metrics"
    funding_rate_table_name = "binance_futures_funding_rate"
    open_interest_table_name = "binance_futures_open_interest"
    implied_vol_table_name = "implied_volatility"

    logger.info("Iniciando processo para %s (%s)...", DEFAULT_SYMBOL, DEFAULT_INTERVAL)

    # --- FASE 1: COLETA DE DADOS E ATUALIZAÇÃO DO BANCO DE DADOS ---
    logger.info("--- FASE 1: COLETA DE DADOS E ATUALIZAÇÃO DO BANCO DE DADOS ---")
    
    # Coleta 1.1: Dados de Velas (OHLCV)
    last_timestamp_klines = get_last_timestamp_from_db(klines_table_name, DB_FILE)
    if not last_timestamp_klines:
        start_time_ms_klines = int((datetime.now() - timedelta(days=DEFAULT_HISTORICAL_DAYS)).timestamp() * 1000)
    else:
        start_time_ms_klines = last_timestamp_klines
    df_klines_new = fetch_all_klines(DEFAULT_SYMBOL, DEFAULT_INTERVAL, start_time_ms_klines, int(time.time() * 1000))
    if not df_klines_new.empty:
        logger.info("Total de %d novas velas coletadas.", len(df_klines_new))
        save_klines_to_db(df_klines_new, klines_table_name, DB_FILE)
    else:
        logger.warning("Nenhuma nova vela foi coletada.")
    
    # Coleta 1.2: Fear and Greed Index
    last_timestamp_fng_sec = get_last_fng_timestamp_from_db(fng_table_name, DB_FILE)
    fng_data_new = get_fear_and_greed_index(limit=365) if not last_timestamp_fng_sec else get_fear_and_greed_index(limit=365, start_date_unix_sec=last_timestamp_fng_sec)
    if fng_data_new:
        save_fng_to_db(fng_data_new, fng_table_name, DB_FILE)

    # Coleta 1.3: Dados On-Chain
    on_chain_data = get_bitcoin_network_fees()
    if on_chain_data:
        save_on_chain_to_db(on_chain_data, on_chain_table_name, DB_FILE)
    
    # Coleta 1.4: Funding Rate
    funding_rate_data = get_funding_rate_history(symbol=DEFAULT_SYMBOL)
    if funding_rate_data:
        save_funding_rate_to_db(funding_rate_data, funding_rate_table_name, DB_FILE)

    # Coleta 1.5: Open Interest
    open_interest_data = get_open_interest(symbol=DEFAULT_SYMBOL)
    if open_interest_data:
        save_open_interest_to_db(open_interest_data, open_interest_table_name, DB_FILE)

    # Coleta 1.6: Implied Volatility (Deribit BTC_DVOL)
    last_iv_ts = get_last_implied_volatility_timestamp_from_db(implied_vol_table_name, DB_FILE)
    # Se não tivermos timestamp anterior, buscar histórico dos últimos DEFAULT_HISTORICAL_DAYS dias
    if not last_iv_ts:
        start_ts_iv = int((datetime.now() - timedelta(days=DEFAULT_HISTORICAL_DAYS)).timestamp() * 1000)
    else:
        start_ts_iv = last_iv_ts

    iv_data = get_implied_volatility_history(index_name="BTC_DVOL", resolution="1D", start_timestamp_ms=start_ts_iv, end_timestamp_ms=int(time.time() * 1000), limit=1000)
    if iv_data:
        save_implied_volatility_to_db(iv_data, implied_vol_table_name, DB_FILE)

    # --- FASE 2: CARREGAMENTO DE DADOS E CÁLCULO DE INDICADORES ---
    logger.info("--- FASE 2: CARREGAMENTO DE DADOS E CÁLCULO DE INDICADORES ---")
    all_klines_df = get_data_from_db(klines_table_name, DB_FILE)
    
    if all_klines_df.empty:
        logger.warning("Não há dados suficientes no banco de dados para continuar. Encerrando.")
        return
        
    logger.info("DataFrame de velas carregado com %d velas para cálculo.", len(all_klines_df))
    
    # Adicionar Volume On-Chain como proxy do volume de klines
    all_klines_df['Vol_onchain'] = all_klines_df['Volume']
    
    # Calcular Indicadores Técnicos
    all_klines_df['SMA_20'] = calculate_sma(all_klines_df, column='Close', window=20)
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

    # --- FASE 3: CÁLCULO DE INDICADORES COMPOSTOS ---
    logger.info("--- FASE 3: CÁLCULO DE INDICADORES COMPOSTOS ---")

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
            
            # --- LÓGICA DE PREENCHIMENTO ROBUSTA ---
            # 1. Preenche para frente (carrega o último valor válido para os dias seguintes)
            all_klines_df['Sentimento_Score'].ffill(inplace=True)
            # 2. Preenche para trás (pega o próximo valor válido e preenche os dias anteriores)
            all_klines_df['Sentimento_Score'].bfill(inplace=True)
            
            all_klines_df.drop(columns=['Date'], inplace=True)

    # --- Merge Implied Volatility ---
    iv_df = get_implied_volatility_data_from_db(implied_vol_table_name, DB_FILE)
    if not iv_df.empty:
        iv_df['Date'] = iv_df['Timestamp'].dt.date
        daily_iv = iv_df.groupby('Date').last().reset_index()[['Date', 'Volatility']]
        daily_iv.rename(columns={'Volatility': 'Implied_Volatility'}, inplace=True)

        all_klines_df['Date'] = all_klines_df['Open_time'].dt.date
        all_klines_df = pd.merge(all_klines_df, daily_iv, on='Date', how='left')
        # Propagate values forward/backward to align with intraday candles
        all_klines_df['Implied_Volatility'].ffill(inplace=True)
        all_klines_df['Implied_Volatility'].bfill(inplace=True)
        all_klines_df.drop(columns=['Date'], inplace=True)
    else:
        logger.warning("Nenhum dado de Implied Volatility disponível; Volatilidade será baseada em fallback (ATR).")

    # Garante que os scores sejam calculados e não contenham NaN
    if 'Sentimento_Score' in all_klines_df.columns and not all_klines_df['Sentimento_Score'].isnull().all():
        all_klines_df['Volatilidade_Score'] = calculate_composite_volatility(all_klines_df, atr_col='ATR')
        all_klines_df['Oportunidade_Score'] = calculate_composite_opportunity(all_klines_df, volume_onchain_col='Vol_onchain')

        # Preenche qualquer NaN restante com um valor neutro (0.5) como segurança final
        all_klines_df[['Sentimento_Score', 'Volatilidade_Score', 'Oportunidade_Score']] = all_klines_df[['Sentimento_Score', 'Volatilidade_Score', 'Oportunidade_Score']].fillna(0.5)
    else:
        logger.warning("Aviso: Score de Sentimento não pôde ser calculado. Scores compostos serão preenchidos com valor neutro.")
        all_klines_df['Sentimento_Score'] = 0.5
        all_klines_df['Volatilidade_Score'] = 0.5
        all_klines_df['Oportunidade_Score'] = 0.5

    # --- FASE 4: BACKTEST, GERAÇÃO DE SINAIS E RELATÓRIOS ---
    logger.info("--- FASE 4: BACKTEST, GERAÇÃO DE SINAIS E RELATÓRIOS ---")
    initial_capital = 1000
    backtest_results = run_backtest(all_klines_df, initial_capital_usd=initial_capital)
    
    # Exibe o relatório de backtest
    logger.info("--- RELATÓRIO DE BACKTEST ---")
    logger.info("Capital Inicial: $%0.2f", backtest_results['initial_capital_usd'])
    logger.info("Capital Final: $%0.2f", backtest_results['final_usd_value'])
    logger.info("Lucro/Prejuízo: $%0.2f (%0.2f%%)", backtest_results['profit_usd'], backtest_results['profit_percentage_usd'])
    logger.info("Performance do Buy and Hold (BTC): (%0.2f%%)", backtest_results['btc_benchmark_profit_percentage'])

    # Exibe os indicadores e resultados
    logger.info("--- RESUMO DOS INDICADORES RECENTES ---")
    df_display = all_klines_df.dropna().tail(5).copy()
    logger.info("[ TENDÊNCIA ]\n%s", df_display[['Open_time', 'Close', 'SMA_20', 'EMA_20', 'MACD', 'MACD_Signal']].to_string())
    logger.info("[ MOMENTUM e VOLATILIDADE ]\n%s", df_display[['Open_time', 'RSI', 'Stoch_K', 'Stoch_D', 'BB_Upper', 'BB_Lower', 'ATR']].to_string())
    logger.info("[ FLUXO ]\n%s", df_display[['Open_time', 'OBV']].to_string())
    logger.info("[ INDICADORES COMPOSTOS ]\n%s", df_display[['Open_time', 'Sentimento_Score', 'Volatilidade_Score', 'Oportunidade_Score']].to_string())
    
    logger.info("--- EXIBINDO DADOS RECENTES ---")
    fng_df = get_fng_data_from_db(fng_table_name, DB_FILE)
    if not fng_df.empty:
        logger.info("--- Fear and Greed Index Recente ---\n%s", fng_df.tail(5))
    conn = create_connection(DB_FILE)
    if conn:
        try:
            on_chain_df = pd.read_sql("SELECT * FROM " + on_chain_table_name + " ORDER BY Timestamp DESC LIMIT 5", conn)
            on_chain_df['Timestamp'] = pd.to_datetime(on_chain_df['Timestamp'], unit='ms')
            logger.info("--- Dados On-Chain Recentes ---\n%s", on_chain_df.to_string())
            funding_rate_df = pd.read_sql("SELECT * FROM " + funding_rate_table_name + " ORDER BY FundingTime DESC LIMIT 5", conn)
            funding_rate_df['FundingTime'] = pd.to_datetime(funding_rate_df['FundingTime'], unit='ms')
            logger.info("--- Funding Rate Recente ---\n%s", funding_rate_df.to_string())
            open_interest_df = pd.read_sql("SELECT * FROM " + open_interest_table_name + " ORDER BY Timestamp DESC LIMIT 5", conn)
            open_interest_df['Timestamp'] = pd.to_datetime(open_interest_df['Timestamp'], unit='ms')
            logger.info("--- Open Interest Recente ---\n%s", open_interest_df.to_string())
        except pd.io.sql.DatabaseError:
            logger.warning("Alguma das tabelas recentes não existe ou está vazia.")
        finally:
            conn.close()

    # --- GERAÇÃO DE DECISÃO DE TRADE EM TEMPO REAL ---
    latest_data = all_klines_df.dropna().tail(1)

    if not latest_data.empty:
        # Usa a estratégia principal para tomar a decisão
        latest_decision = decide_liquidity(
            latest_data,
            sentiment_col='Sentimento_Score',
            volatility_col='Volatilidade_Score',
            opportunity_col='Oportunidade_Score'
        ).iloc[-1]

        logger.info("Decisão de liquidez mais recente: %s", latest_decision.upper())
    else:
        logger.warning("Não foi possível gerar uma decisão; dados insuficientes.")

    logger.info("Processamento do sistema de trade concluído.")

