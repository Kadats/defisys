import logging
import time
from datetime import datetime, timedelta
import pandas as pd

from backend.src.config import (
    DEFAULT_SYMBOL, DEFAULT_INTERVAL, BINANCE_FUTURES_API_BASE_URL
)
from backend.src.data import sources, storage

# Setup logging for the sync script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataSync")

def backfill_derivatives(months: int = 12):
    """
    Sincroniza o histórico real de Funding Rate e Open Interest da Binance Futures API.
    Lida com paginação para cobrir o período desejado (ex: 12 meses).
    """
    logger.info(f"Iniciando hidratação de dados de derivativos...")
    
    # Busca a última data de OI no banco, ou começa de 2024-01-01
    last_oi_ts = storage.get_last_open_interest_timestamp_from_db("binance_futures_open_interest")
    if last_oi_ts:
        start_ts_ms = last_oi_ts
        logger.info(f"Continuando coleta a partir de {pd.to_datetime(start_ts_ms, unit='ms')}")
    else:
        # Fallback para 2024-01-01
        start_ts_ms = int(datetime(2024, 1, 1).timestamp() * 1000)
        logger.info("Iniciando coleta do zero a partir de 2024-01-01")
        
    end_date = datetime.now()
    end_ts_ms = int(end_date.timestamp() * 1000)
    
    funding_rate_table = "binance_futures_funding_rate"
    open_interest_table = "binance_futures_open_interest"
    
    # --- 1. Funding Rate Backfill ---
    logger.info("=== Sincronizando Funding Rate ===")
    current_start = start_ts_ms
    total_funding_collected = 0
    
    while current_start < end_ts_ms:
        data = sources.get_funding_rate_history(
            symbol=DEFAULT_SYMBOL,
            limit=1000,
            start_time_ms=current_start,
            end_time_ms=end_ts_ms,
            binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL
        )
        
        if not data:
            logger.info("Nenhum dado adicional de Funding Rate encontrado. Fim da coleta.")
            break
            
        storage.save_funding_rate_to_db(data, funding_rate_table)
        total_funding_collected += len(data)
        
        last_item_ts = data[-1].get('fundingTime')
        logger.info(f"Coletados {len(data)} registros de Funding Rate. Total: {total_funding_collected}")
        
        if last_item_ts and last_item_ts > current_start:
            current_start = last_item_ts + 1
        else:
            break
            
        time.sleep(0.5)

    # --- 2. Open Interest Backfill ---
    logger.info("=== Sincronizando Open Interest ===")
    current_start = start_ts_ms
    # Se start_ts_ms for muito antigo (mais de 30 dias), Binance pode rejeitar.
    # Vamos tentar o que foi pedido, mas se falhar com 400, tentaremos os últimos 30 dias.
    thirty_days_ago_ts = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    
    total_oi_collected = 0
    import requests
    
    while current_start < end_ts_ms:
        batch_end = min(current_start + (30 * 24 * 60 * 60 * 1000), end_ts_ms)
        
        data = None
        backoff_delays = [5, 15, 60]
        
        for attempt, delay in enumerate(backoff_delays + [0]):
            try:
                data = sources.get_open_interest_history(
                    symbol=DEFAULT_SYMBOL,
                    period=DEFAULT_INTERVAL,
                    limit=500,
                    start_time_ms=current_start,
                    end_time_ms=batch_end,
                    binance_futures_api_base_url=BINANCE_FUTURES_API_BASE_URL
                )
                break  # Sucesso!
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 400:
                    if current_start < thirty_days_ago_ts:
                        logger.warning(f"Data {pd.to_datetime(current_start, unit='ms')} rejeitada (provavelmente limite de 30 dias). Saltando para 30 dias atrás.")
                        current_start = thirty_days_ago_ts
                        # Break inner loop to retry with new current_start
                        data = None
                        break 
                    else:
                        logger.warning(f"Recebido Erro 400 da Binance em data recente. Finalizando coleta de OI.")
                        data = []
                        break
                elif attempt < len(backoff_delays):
                    logger.warning(f"Erro HTTP {e.response.status_code if e.response else ''}. Retentando em {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error("Falha após todas as tentativas.")
                    data = []
            except requests.exceptions.RequestException as e:
                if attempt < len(backoff_delays):
                    logger.warning(f"Timeout/Conexão Falhou: {e}. Retentando em {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error("Falha após todas as tentativas.")
                    data = []

        if data is None: # Casos de skip/retry interno
            continue

        if not data:
            logger.info("Nenhum dado adicional de Open Interest encontrado ou chegamos ao limite real. Fim da coleta.")
            break
            
        storage.save_open_interest_to_db(data, open_interest_table)
        total_oi_collected += len(data)
        
        last_item_ts = data[-1].get('timestamp')
        logger.info(f"Coletados {len(data)} registros de Open Interest no lote. Total: {total_oi_collected}")
        
        if last_item_ts and last_item_ts > current_start:
            current_start = last_item_ts + 1
        else:
            current_start = batch_end + 1
            
        time.sleep(0.5)

    logger.info("=== Hidratação de Derivativos Concluída ===")

if __name__ == "__main__":
    backfill_derivatives(12)