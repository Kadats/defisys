import logging
from datetime import datetime, timedelta
from typing import Optional
import psycopg2
from psycopg2.extensions import connection as PGConnection

import backend.src.config as config

logger = logging.getLogger(__name__)

def create_connection() -> Optional[PGConnection]:
    """Creates a connection to the PostgreSQL database."""
    try:
        # Use config.DATABASE_URL dynamically so tests can override it
        conn = psycopg2.connect(config.DATABASE_URL)
        logger.debug(f"Successfully connected to PostgreSQL database")
        return conn
    except (psycopg2.Error, Exception) as e:
        logger.error(f"Error connecting to PostgreSQL database: {e}")
        return None

def get_start_timestamp_for_collection(get_last_ts_func, table_name: str, historical_days: int) -> int:
    """Determines the start timestamp for a new data collection."""
    last_ts = get_last_ts_func(table_name)
    if last_ts:
        return last_ts
    return int((datetime.now() - timedelta(days=historical_days)).timestamp() * 1000)
