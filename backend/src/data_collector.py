import requests
import json
import time
import pandas as pd
from .config import BINANCE_API_BASE_URL, DEFAULT_KLINES_LIMIT, FNG_API_URL, BLOCKCHAIR_API_URL, BINANCE_FUTURES_API_BASE_URL


# Coletas Binance
def get_klines_from_api(symbol: str, interval: str, limit: int = DEFAULT_KLINES_LIMIT, end_time: int = None) -> list:
    """
    Coleta dados de velas (OHLCV) da API da Binance.

    Args:
        symbol (str): O par de trading (ex: "BTCUSDT").
        interval (str): O período da vela (ex: "1h", "1d").
        limit (int): O número máximo de velas a serem retornadas (max 1000).
        end_time (int): O timestamp de término em milissegundos (opcional).

    Returns:
        list: Uma lista de velas OHLCV.
    """
    endpoint = f"{BINANCE_API_BASE_URL}/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    if end_time:
        params["endTime"] = end_time

    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar à API da Binance para klines: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Erro ao decodificar a resposta JSON: {response.text}")
        return []
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao obter klines: {e}")
        return []

def fetch_all_klines(symbol: str, interval: str, start_timestamp: int, end_timestamp: int, max_klines_per_request: int = DEFAULT_KLINES_LIMIT) -> pd.DataFrame:
    """
    Coleta todas as velas entre start_timestamp e end_timestamp, lidando com o limite da API.

    Args:
        symbol (str): O par de trading (ex: "BTCUSDT").
        interval (str): O período da vela (ex: "1h", "1d").
        start_timestamp (int): Timestamp de início em milissegundos.
        end_timestamp (int): Timestamp de término em milissegundos.
        max_klines_per_request (int): Limite máximo de velas por requisição da API.

    Returns:
        pd.DataFrame: Um DataFrame Pandas com os dados OHLCV.
    """
    all_data = []
    current_end_time = end_timestamp

    while True:
        klines = get_klines_from_api(symbol, interval, max_klines_per_request, current_end_time)
        if not klines:
            break

        klines_df = pd.DataFrame(klines, columns=[
            'Open_time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close_time', 'Quote_asset_volume', 'Number_of_trades',
            'Taker_buy_base_asset_volume', 'Taker_buy_quote_asset_volume', 'Ignore'
        ])
        
        klines_df['Open_time'] = pd.to_datetime(klines_df['Open_time'], unit='ms')
        klines_df['Close_time'] = pd.to_datetime(klines_df['Close_time'], unit='ms')
        
        # Converte colunas numéricas para float (originalmente são strings)
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 
                        'Quote_asset_volume', 'Taker_buy_base_asset_volume', 'Taker_buy_quote_asset_volume']
        for col in numeric_cols:
            klines_df[col] = pd.to_numeric(klines_df[col])

        if 'Ignore' in klines_df.columns:
            klines_df = klines_df.drop(columns=['Ignore'])

        klines_df = klines_df[klines_df['Open_time'] >= pd.to_datetime(start_timestamp, unit='ms')]
        
        if klines_df.empty:
            break

        all_data.insert(0, klines_df)
        
        current_end_time = klines_df['Open_time'].min().value // 10**6 - 1

        if klines_df['Open_time'].min() <= pd.to_datetime(start_timestamp, unit='ms'):
            break

        time.sleep(0.1)

    if all_data:
        final_df = pd.concat(all_data).drop_duplicates(subset=['Open_time']).sort_values('Open_time').reset_index(drop=True)
        return final_df
    return pd.DataFrame()

def get_funding_rate_history(symbol: str, limit: int = 100) -> list:
    """
    Coleta o histórico de Funding Rate da API da Binance Futures.

    Args:
        symbol (str): O par de trading (ex: "BTCUSDT").
        limit (int): O número de entradas a retornar (máximo 1000).

    Returns:
        list: Uma lista de dicionários com os dados do Funding Rate, ou uma lista vazia.
    """
    endpoint = f"{BINANCE_FUTURES_API_BASE_URL}/fapi/v1/fundingRate"
    params = {
        "symbol": symbol,
        "limit": limit
    }

    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar à API da Binance Futures para Funding Rate: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Erro ao decodificar a resposta JSON do Funding Rate: {response.text}")
        return []
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao obter o Funding Rate: {e}")
        return []

def get_open_interest(symbol: str) -> dict:
    """
    Coleta o Open Interest atual da API da Binance Futures.

    Args:
        symbol (str): O par de trading (ex: "BTCUSDT").

    Returns:
        dict: Um dicionário com os dados do Open Interest, ou None em caso de erro.
    """
    endpoint = f"{BINANCE_FUTURES_API_BASE_URL}/fapi/v1/openInterest"
    params = {
        "symbol": symbol
    }

    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar à API da Binance Futures para Open Interest: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Erro ao decodificar a resposta JSON do Open Interest: {response.text}")
        return None
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao obter o Open Interest: {e}")
        return None


# Coletas Fear and Greed Index
def get_fear_and_greed_index(limit: int = 1, start_date_unix_sec: int = None) -> list: # Modificado para retornar lista
    """
    Coleta o Fear and Greed Index da Alternative.me API.

    Args:
        limit (int): Número de dias de dados a retornar (padrão: 1 para o mais recente).
        start_date_unix_sec (int): Timestamp de início em segundos Unix (opcional).

    Returns:
        list: Uma lista de dicionários contendo os dados do índice, ou lista vazia em caso de erro.
    """
    params = {"limit": limit}
    if start_date_unix_sec:
        params["date_from"] = start_date_unix_sec # A API FNG usa 'date_from'
    
    try:
        response = requests.get(FNG_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if data and 'data' in data and len(data['data']) > 0:
            # A API retorna os dados mais recentes primeiro, precisamos inverter para o DB
            return list(reversed(data['data']))
        return []
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar à API do Fear and Greed Index: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Erro ao decodificar a resposta JSON do Fear and Greed Index: {response.text}")
        return []
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao obter Fear and Greed Index: {e}")
        return []


# Coletas On-Chain Blockchair    
def get_bitcoin_network_fees() -> dict:
    """
    Coleta estatísticas básicas da rede Bitcoin, incluindo taxas de transação.

    Returns:
        dict: Um dicionário com as estatísticas da rede, ou None em caso de erro.
    """
    try:
        response = requests.get(BLOCKCHAIR_API_URL)
        response.raise_for_status()
        data = response.json()

        if data and 'data' in data:
            return data['data']
        return None
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar à API da Blockchair: {e}")
        return None
    except json.JSONDecodeError:
        print(f"Erro ao decodificar a resposta JSON da Blockchair: {response.text}")
        return None
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao obter dados on-chain: {e}")
        return None
    
