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
from .config import DB_FILE, DEFAULT_SYMBOL, DEFAULT_INTERVAL, DEFAULT_HISTORICAL_DAYS

# Importa o módulo de indicadores
from .indicators import (
    calculate_sma, calculate_ema, calculate_rsi, calculate_macd,
    calculate_bollinger_bands, calculate_stochastic_oscillator,
    calculate_obv, calculate_atr, calculate_fibonacci_retracements,
    calculate_composite_sentiment, calculate_composite_volatility, 
    calculate_composite_opportunity
)

# Estratégias
from .strategies import generate_signals

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

    print(f"Iniciando processo para {DEFAULT_SYMBOL} ({DEFAULT_INTERVAL})...")

    # --- FASE 1: COLETA DE DADOS E ATUALIZAÇÃO DO BANCO DE DADOS ---
    print("\n--- FASE 1: COLETA DE DADOS E ATUALIZAÇÃO DO BANCO DE DADOS ---")
    
    # Coleta 1.1: Dados de Velas (OHLCV)
    last_timestamp_klines = get_last_timestamp_from_db(klines_table_name, DB_FILE)
    if not last_timestamp_klines:
        start_time_ms_klines = int((datetime.now() - timedelta(days=DEFAULT_HISTORICAL_DAYS)).timestamp() * 1000)
    else:
        start_time_ms_klines = last_timestamp_klines
    df_klines_new = fetch_all_klines(DEFAULT_SYMBOL, DEFAULT_INTERVAL, start_time_ms_klines, int(time.time() * 1000))
    if not df_klines_new.empty:
        print(f"Total de {len(df_klines_new)} novas velas coletadas.")
        save_klines_to_db(df_klines_new, klines_table_name, DB_FILE)
    else:
        print("Nenhuma nova vela foi coletada.")
    
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

    # --- FASE 2: CARREGAMENTO DE DADOS E CÁLCULO DE INDICADORES ---
    print("\n--- FASE 2: CARREGAMENTO DE DADOS E CÁLCULO DE INDICADORES ---")
    all_klines_df = get_data_from_db(klines_table_name, DB_FILE)
    
    if all_klines_df.empty:
        print("Não há dados suficientes no banco de dados para continuar. Encerrando.")
        return
        
    print(f"DataFrame de velas carregado com {len(all_klines_df)} velas para cálculo.")
    
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
    print("\n--- FASE 3: CÁLCULO DE INDICADORES COMPOSTOS ---")
    
    conn = create_connection(DB_FILE)
    funding_rate_df = pd.read_sql("SELECT FundingTime, FundingRate FROM " + funding_rate_table_name, conn)
    open_interest_df = pd.read_sql("SELECT Timestamp, OpenInterest FROM " + open_interest_table_name, conn)
    on_chain_df = pd.read_sql("SELECT Timestamp, Transactions_24h, Fees_usd_24h FROM " + on_chain_table_name, conn)
    conn.close()

    if not funding_rate_df.empty and not open_interest_df.empty and not on_chain_df.empty:
        funding_rate_df['Timestamp'] = pd.to_datetime(funding_rate_df['FundingTime'], unit='ms')
        open_interest_df['Timestamp'] = pd.to_datetime(open_interest_df['Timestamp'], unit='ms')
        on_chain_df['Timestamp'] = pd.to_datetime(on_chain_df['Timestamp'], unit='ms')

        merged_df = pd.merge(funding_rate_df[['Timestamp', 'FundingRate']], open_interest_df[['Timestamp', 'OpenInterest']], on='Timestamp', how='outer')
        merged_df = pd.merge(merged_df, on_chain_df[['Timestamp', 'Transactions_24h']], on='Timestamp', how='outer')
        merged_df = pd.merge(merged_df, on_chain_df[['Timestamp', 'Fees_usd_24h']], on='Timestamp', how='outer') # Adicionado Fees_usd_24h
        
        merged_df = merged_df.sort_values(by='Timestamp').reset_index(drop=True)
        merged_df = merged_df.ffill().dropna().reset_index(drop=True)

        if not merged_df.empty:
            all_klines_df['Sentimento_Score'] = calculate_composite_sentiment(merged_df['FundingRate'], merged_df['OpenInterest'])
            all_klines_df['Volatilidade_Score'] = calculate_composite_volatility(all_klines_df, atr_col='ATR')
            all_klines_df['Oportunidade_Score'] = calculate_composite_opportunity(all_klines_df, volume_onchain_col='Vol_onchain')
        else:
            print("Erro: Não foi possível alinhar os dados de indicadores compostos.")
            all_klines_df['Sentimento_Score'] = None
            all_klines_df['Volatilidade_Score'] = None
            all_klines_df['Oportunidade_Score'] = None
    else:
        print("Erro: Um ou mais DataFrames para indicadores compostos estão vazios.")
        all_klines_df['Sentimento_Score'] = None
        all_klines_df['Volatilidade_Score'] = None
        all_klines_df['Oportunidade_Score'] = None

    # --- FASE 4: BACKTEST, GERAÇÃO DE SINAIS E RELATÓRIOS ---
    print("\n--- FASE 4: BACKTEST, GERAÇÃO DE SINAIS E RELATÓRIOS ---")
    initial_capital = 1000
    backtest_results = run_backtest(all_klines_df, initial_capital_usd=initial_capital)
    
    # Exibe o relatório de backtest
    print("\n--- RELATÓRIO DE BACKTEST ---")
    print(f"Capital Inicial: ${backtest_results['initial_capital_usd']:.2f}")
    print(f"Capital Final: ${backtest_results['final_usd_value']:.2f}")
    print(f"Lucro/Prejuízo: ${backtest_results['profit_usd']:.2f} ({backtest_results['profit_percentage_usd']:.2f}%)")
    print(f"Performance do Buy and Hold (BTC): ({backtest_results['btc_benchmark_profit_percentage']:.2f}%)")

    # Exibe os indicadores e resultados
    print("\n--- RESUMO DOS INDICADORES RECENTES ---")
    df_display = all_klines_df.dropna().tail(5).copy()
    print("\n[ TENDÊNCIA ]")
    print(df_display[['Open_time', 'Close', 'SMA_20', 'EMA_20', 'MACD', 'MACD_Signal']].to_string())
    print("\n[ MOMENTUM e VOLATILIDADE ]")
    print(df_display[['Open_time', 'RSI', 'Stoch_K', 'Stoch_D', 'BB_Upper', 'BB_Lower', 'ATR']].to_string())
    print("\n[ FLUXO ]")
    print(df_display[['Open_time', 'OBV']].to_string())
    print("\n[ INDICADORES COMPOSTOS ]")
    print(df_display[['Open_time', 'Sentimento_Score', 'Volatilidade_Score', 'Oportunidade_Score']].to_string())
    
    print("\n--- EXIBINDO DADOS RECENTES ---")
    fng_df = get_fng_data_from_db(fng_table_name, DB_FILE)
    if not fng_df.empty:
        print("\n--- Fear and Greed Index Recente ---")
        print(fng_df.tail(5))
    conn = create_connection(DB_FILE)
    if conn:
        try:
            on_chain_df = pd.read_sql("SELECT * FROM " + on_chain_table_name + " ORDER BY Timestamp DESC LIMIT 5", conn)
            on_chain_df['Timestamp'] = pd.to_datetime(on_chain_df['Timestamp'], unit='ms')
            print("\n--- Dados On-Chain Recentes ---")
            print(on_chain_df.to_string())
            funding_rate_df = pd.read_sql("SELECT * FROM " + funding_rate_table_name + " ORDER BY FundingTime DESC LIMIT 5", conn)
            funding_rate_df['FundingTime'] = pd.to_datetime(funding_rate_df['FundingTime'], unit='ms')
            print("\n--- Funding Rate Recente ---")
            print(funding_rate_df.to_string())
            open_interest_df = pd.read_sql("SELECT * FROM " + open_interest_table_name + " ORDER BY Timestamp DESC LIMIT 5", conn)
            open_interest_df['Timestamp'] = pd.to_datetime(open_interest_df['Timestamp'], unit='ms')
            print("\n--- Open Interest Recente ---")
            print(open_interest_df.to_string())
        except pd.io.sql.DatabaseError:
            print("Alguma das tabelas recentes não existe ou está vazia.")
        finally:
            conn.close()

    # --- GERAÇÃO DE SINAIS DE TRADE EM TEMPO REAL ---
    df_with_signals_real_time = generate_signals(all_klines_df.tail(1))
    latest_signal = df_with_signals_real_time['Signal'].iloc[-1]
    print(f"\nSinal de trade mais recente: {latest_signal}")
    
    print("\nProcessamento do sistema de trade concluído.")

