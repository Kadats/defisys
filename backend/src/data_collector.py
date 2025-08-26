import json
import time
import logging
from typing import Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import (
    BINANCE_API_BASE_URL,
    DEFAULT_KLINES_LIMIT,
    FNG_API_URL,
    BLOCKCHAIR_API_URL,
    BINANCE_FUTURES_API_BASE_URL,
)

logger = logging.getLogger(__name__)


class APIClient:
    """HTTP client with Session, retries and exponential backoff.

    This client is safe to reuse across calls and APIs. It mounts a
    `HTTPAdapter` configured with `urllib3.util.Retry` so transient errors
    (connection errors, timeouts, and 5xx responses) are retried using
    exponential backoff.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        status_forcelist=(500, 502, 503, 504),
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout = timeout
        self.session = requests.Session()

        retry = Retry(
            total=max_retries,
            read=max_retries,
            connect=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=("GET", "POST"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _build_url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        if self.base_url:
            return f"{self.base_url.rstrip('/')}/{path_or_url.lstrip('/')}"
        return path_or_url

    def get(self, path_or_url: str, params: dict = None, headers: dict = None) -> requests.Response:
        url = self._build_url(path_or_url)
        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
            # If status is 5xx and Retry allowed, urllib3 will have retried according to policy.
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as exc:
            # Let caller handle/log final failure
            raise


# Create per-API clients to reuse connections and retry behavior
_binance_client = APIClient(base_url=BINANCE_API_BASE_URL, timeout=10, max_retries=3, backoff_factor=1)
_binance_futures_client = APIClient(base_url=BINANCE_FUTURES_API_BASE_URL, timeout=10, max_retries=3, backoff_factor=1)
_fng_client = APIClient(base_url=FNG_API_URL, timeout=10, max_retries=2, backoff_factor=0.5)
_blockchair_client = APIClient(base_url=BLOCKCHAIR_API_URL, timeout=10, max_retries=2, backoff_factor=0.5)
_deribit_client = APIClient(base_url="https://www.deribit.com/api/v2", timeout=10, max_retries=3, backoff_factor=1)


# Coletas Binance
def get_klines_from_api(symbol: str, interval: str, limit: int = DEFAULT_KLINES_LIMIT, end_time: int = None) -> list:
    """Coleta dados de velas (OHLCV) da API da Binance.

    Mantém a assinatura e o comportamento de retorno (lista) inalterados.
    """
    endpoint = "/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    if end_time:
        params["endTime"] = end_time

    try:
        resp = _binance_client.get(endpoint, params=params)
        try:
            return resp.json()
        except json.JSONDecodeError:
            logger.error("Erro ao decodificar a resposta JSON da Binance (klines): %s", resp.text)
            return []
    except requests.exceptions.RequestException as e:
        logger.error("Erro ao conectar à API da Binance para klines (url=%s): %s", _binance_client._build_url(endpoint), e)
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
    endpoint = "/fapi/v1/fundingRate"
    params = {"symbol": symbol, "limit": limit}
    try:
        resp = _binance_futures_client.get(endpoint, params=params)
        try:
            return resp.json()
        except json.JSONDecodeError:
            logger.error("Erro ao decodificar a resposta JSON do Funding Rate: %s", resp.text)
            return []
    except requests.exceptions.RequestException as e:
        logger.error("Erro ao conectar à API da Binance Futures para Funding Rate (url=%s): %s", _binance_futures_client._build_url(endpoint), e)
        return []

def get_open_interest(symbol: str) -> dict:
    """
    Coleta o Open Interest atual da API da Binance Futures.

    Args:
        symbol (str): O par de trading (ex: "BTCUSDT").

    Returns:
        dict: Um dicionário com os dados do Open Interest, ou None em caso de erro.
    """
    endpoint = "/fapi/v1/openInterest"
    params = {"symbol": symbol}
    try:
        resp = _binance_futures_client.get(endpoint, params=params)
        try:
            return resp.json()
        except json.JSONDecodeError:
            logger.error("Erro ao decodificar a resposta JSON do Open Interest: %s", resp.text)
            return None
    except requests.exceptions.RequestException as e:
        logger.error("Erro ao conectar à API da Binance Futures para Open Interest (url=%s): %s", _binance_futures_client._build_url(endpoint), e)
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
        params["date_from"] = start_date_unix_sec  # A API FNG usa 'date_from'

    try:
        # FNG API URL may be full; use client get with explicit URL
        resp = _fng_client.get(FNG_API_URL, params=params)
        try:
            data = resp.json()
        except json.JSONDecodeError:
            logger.error("Erro ao decodificar a resposta JSON do Fear and Greed Index: %s", resp.text)
            return []

        if data and "data" in data and len(data["data"]) > 0:
            # A API retorna os dados mais recentes primeiro, precisamos inverter para o DB
            return list(reversed(data["data"]))
        return []
    except requests.exceptions.RequestException as e:
        logger.error("Erro ao conectar à API do Fear and Greed Index (url=%s): %s", FNG_API_URL, e)
        return []


# Coletas On-Chain Blockchair    
def get_bitcoin_network_fees() -> dict:
    """
    Coleta estatísticas básicas da rede Bitcoin, incluindo taxas de transação.

    Returns:
        dict: Um dicionário com as estatísticas da rede, ou None em caso de erro.
    """
    try:
        resp = _blockchair_client.get(BLOCKCHAIR_API_URL)
        try:
            data = resp.json()
        except json.JSONDecodeError:
            logger.error("Erro ao decodificar a resposta JSON da Blockchair: %s", resp.text)
            return None

        if data and "data" in data:
            return data["data"]
        return None
    except requests.exceptions.RequestException as e:
        logger.error("Erro ao conectar à API da Blockchair (url=%s): %s", BLOCKCHAIR_API_URL, e)
        return None
    except Exception as e:
        logger.exception("Ocorreu um erro inesperado ao obter dados on-chain: %s", e)
        return None


def get_implied_volatility_history(index_name: str = "BTC_DVOL", resolution: str = "1D", start_timestamp_ms: int = None, end_timestamp_ms: int = None, limit: int = 1000) -> list:
    """Busca o histórico de volatilidade implícita do índice Deribit (ex: BTC_DVOL).

    Retorna uma lista de dicionários com chaves 'timestamp' (ms) e 'volatility'. Mantém assinatura
    simples para não quebrar chamadas existentes.
    """
    endpoint = "/public/get_volatility_index_data"
    # Deribit expects 'index_name' as the parameter name
    params = {
        "index_name": index_name,
        "resolution": resolution,
        "limit": limit,
    }
    if start_timestamp_ms:
        # Deribit API expects timestamps in milliseconds
        params["start_timestamp"] = int(start_timestamp_ms)
    if end_timestamp_ms:
        params["end_timestamp"] = int(end_timestamp_ms)

    try:
        resp = _deribit_client.get(endpoint, params=params)
        try:
            payload = resp.json()
        except json.JSONDecodeError:
            logger.error("Erro ao decodificar JSON da Deribit (IV): %s", resp.text)
            return []

        # payload format: {"jsonrpc":"2.0","result":{...}} or result directly
        result = payload.get("result") if isinstance(payload, dict) else payload
        if not result:
            logger.error("Resposta inesperada da Deribit para IV: %s", payload)
            return []

        # Deribit may return arrays of timestamps and values, or a list of dicts
        out = []
        # Case A: result contains 'data' as list of dicts
        if isinstance(result, dict) and "data" in result and isinstance(result["data"], list):
            for item in result["data"]:
                ts = item.get("timestamp") or item.get("t")
                vol = item.get("value") or item.get("volatility") or item.get("v")
                if ts is None or vol is None:
                    continue
                out.append({"timestamp": int(ts), "volatility": float(vol)})
            return out

        # Case B: result contains parallel arrays 'timestamps' and 'values' or 'values'
        if isinstance(result, dict) and ("timestamps" in result and "values" in result):
            ts_list = result.get("timestamps")
            val_list = result.get("values")
            for ts, val in zip(ts_list, val_list):
                out.append({"timestamp": int(ts), "volatility": float(val)})
            return out

        # Case C: result itself is a list of {timestamp, value}
        if isinstance(result, list):
            for item in result:
                ts = item.get("timestamp") or item.get("t")
                vol = item.get("value") or item.get("volatility") or item.get("v")
                if ts is None or vol is None:
                    continue
                out.append({"timestamp": int(ts), "volatility": float(vol)})
            return out

        # Fallback: unexpected format
        logger.error("Formato inesperado de resposta Deribit (IV): %s", payload)
        return []
    except requests.exceptions.RequestException as e:
        logger.error("Erro ao conectar à API Deribit (IV) endpoint %s: %s", _deribit_client._build_url(endpoint), e)
        return []
    
