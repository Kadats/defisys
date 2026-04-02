import logging
from typing import Optional, Any, Dict, List
import psycopg2
from psycopg2 import sql, extras
from psycopg2.extensions import connection as PGConnection
import pandas as pd

from .connection import create_connection

logger = logging.getLogger(__name__)

# ==================== KLINES TABLE ====================

def create_klines_table(conn: PGConnection, table_name: str):
    """Creates a table to store OHLCV data if it doesn't exist."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    open_time BIGINT PRIMARY KEY,
                    open DOUBLE PRECISION,
                    high DOUBLE PRECISION,
                    low DOUBLE PRECISION,
                    close DOUBLE PRECISION,
                    volume DOUBLE PRECISION,
                    close_time BIGINT,
                    quote_asset_volume DOUBLE PRECISION,
                    number_of_trades INTEGER,
                    taker_buy_base_asset_volume DOUBLE PRECISION,
                    taker_buy_quote_asset_volume DOUBLE PRECISION
                )
            """).format(sql.Identifier(table_name)))
            conn.commit()
            logger.info(f"Table '{table_name}' verified/created successfully.")
    except psycopg2.Error as e:
        logger.error(f"Error creating table '{table_name}': {e}")
        conn.rollback()


def save_klines_to_db(df: pd.DataFrame, table_name: str):
    """Saves a DataFrame of klines to PostgreSQL database."""
    conn = create_connection()
    if not conn:
        return
        
    try:
        create_klines_table(conn, table_name)
        
        df_to_save = df.copy()
        
        # Convert datetime to milliseconds (BIGINT)
        df_to_save['Open_time'] = (df_to_save['Open_time'].values.astype(int) // 10**6).astype(int)
        df_to_save['Close_time'] = (df_to_save['Close_time'].values.astype(int) // 10**6).astype(int)
        
        # Normalize column names to lowercase for PostgreSQL
        df_to_save.columns = [col.lower().replace(' ', '_') for col in df_to_save.columns]
        
        # Use ON CONFLICT DO NOTHING for upsert (PostgreSQL syntax)
        with conn.cursor() as cursor:
            insert_query = sql.SQL("""
                INSERT INTO {} (open_time, open, high, low, close, volume, close_time,
                               quote_asset_volume, number_of_trades, 
                               taker_buy_base_asset_volume, taker_buy_quote_asset_volume)
                VALUES %s
                ON CONFLICT (open_time) DO NOTHING
            """).format(sql.Identifier(table_name))
            
            values = [tuple(row) for row in df_to_save.values]
            extras.execute_values(cursor, insert_query, values)
            
        conn.commit()
        logger.info(f"Data saved/updated in table '{table_name}'")
    except psycopg2.Error as e:
        logger.error(f"Error saving klines data to database: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


def get_last_timestamp_from_db(table_name: str) -> Optional[int]:
    """Gets the timestamp of the last candle saved in the database."""
    conn = create_connection()
    if not conn:
        return None
        
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("SELECT MAX(open_time) FROM {}").format(sql.Identifier(table_name)))
            result = cursor.fetchone()
            last_timestamp = result[0] if result else None
            if last_timestamp:
                return last_timestamp + 1
            return None
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == "42P01":
            logger.warning(f"Table '{table_name}' does not exist yet. Starting fresh.")
            return None
        logger.error(f"Error fetching last timestamp from table '{table_name}': {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_data_from_db(table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
    """Loads data from a PostgreSQL table to a Pandas DataFrame."""
    conn = create_connection()
    if not conn:
        return pd.DataFrame()
        
    try:
        with conn.cursor() as cursor:
            if limit:
                query = sql.SQL("""
                    SELECT * FROM (
                        SELECT * FROM {} ORDER BY open_time DESC LIMIT %s
                    ) subq ORDER BY open_time ASC
                """).format(sql.Identifier(table_name))
                cursor.execute(query, (limit,))
            else:
                query = sql.SQL("SELECT * FROM {} ORDER BY open_time ASC").format(sql.Identifier(table_name))
                cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)
        
        if not df.empty:
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            # Rename columns to match Binance format expected by pipeline
            df.rename(columns={
                'open_time': 'Open_time',
                'close_time': 'Close_time',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume',
                'quote_asset_volume': 'Quote_asset_volume',
                'number_of_trades': 'Number_of_trades',
                'taker_buy_base_asset_volume': 'Taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume': 'Taker_buy_quote_asset_volume'
            }, inplace=True)
        
        return df
    except psycopg2.Error as e:
        logger.error(f"Error loading data from database: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


# ==================== OPEN INTEREST TABLE ====================

def create_open_interest_table(conn: PGConnection, table_name: str):
    """Creates a table to store Open Interest history."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    timestamp BIGINT PRIMARY KEY,
                    symbol TEXT,
                    open_interest DOUBLE PRECISION
                )
            """).format(sql.Identifier(table_name)))
            conn.commit()
            logger.info(f"Table '{table_name}' verified/created for Open Interest.")
    except psycopg2.Error as e:
        logger.error(f"Error creating Open Interest table '{table_name}': {e}")
        conn.rollback()


def save_open_interest_to_db(data: Dict[str, Any], table_name: str):
    """Saves Open Interest data to PostgreSQL database."""
    conn = create_connection()
    if not conn:
        return
        
    try:
        create_open_interest_table(conn, table_name)
        
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
                INSERT INTO {} (timestamp, symbol, open_interest)
                VALUES (%s, %s, %s)
                ON CONFLICT (timestamp) DO NOTHING
            """).format(sql.Identifier(table_name)),
            (data['time'], data['symbol'], float(data['openInterest'])))
            
        conn.commit()
        logger.info(f"Open Interest data saved to table '{table_name}'.")
    except psycopg2.Error as e:
        logger.error(f"Error saving Open Interest data: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


# ==================== FUNDING RATE TABLE ====================

def create_funding_rate_table(conn: PGConnection, table_name: str):
    """Creates a table to store Funding Rate history."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    funding_time BIGINT PRIMARY KEY,
                    symbol TEXT,
                    funding_rate DOUBLE PRECISION
                )
            """).format(sql.Identifier(table_name)))
            conn.commit()
            logger.info(f"Table '{table_name}' verified/created for Funding Rate.")
    except psycopg2.Error as e:
        logger.error(f"Error creating Funding Rate table '{table_name}': {e}")
        conn.rollback()


def save_funding_rate_to_db(data: List[Dict[str, Any]], table_name: str):
    """Saves a list of Funding Rate data to PostgreSQL database."""
    conn = create_connection()
    if not conn:
        return
        
    try:
        create_funding_rate_table(conn, table_name)
        
        rows = [(item['fundingTime'], item['symbol'], float(item['fundingRate'])) for item in data]
        
        with conn.cursor() as cursor:
            insert_query = sql.SQL("""
                INSERT INTO {} (funding_time, symbol, funding_rate)
                VALUES %s
                ON CONFLICT (funding_time) DO NOTHING
            """).format(sql.Identifier(table_name))
            extras.execute_values(cursor, insert_query, rows)
            
        conn.commit()
        logger.info(f"Funding Rate data saved to table '{table_name}'.")
    except psycopg2.Error as e:
        logger.error(f"Error saving Funding Rate data: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


def get_last_funding_rate_timestamp_from_db(table_name: str) -> Optional[int]:
    """Gets the timestamp of the last Funding Rate entry saved in the database (milliseconds)."""
    conn = create_connection()
    if not conn:
        return None
        
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("SELECT MAX(funding_time) FROM {}").format(sql.Identifier(table_name)))
            result = cursor.fetchone()
            last_timestamp_ms = result[0] if result else None
            if last_timestamp_ms:
                return last_timestamp_ms + 1
            return None
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == "42P01":
            logger.warning(f"Table '{table_name}' does not exist yet. Starting fresh.")
            return None
        logger.error(f"Error fetching last Funding Rate timestamp: {e}")
        return None
    finally:
        if conn:
            conn.close()


# ==================== FEAR & GREED INDEX TABLE ====================

def create_fng_table(conn: PGConnection, table_name: str):
    """Creates a table to store Fear and Greed Index data."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    timestamp BIGINT PRIMARY KEY,
                    value INTEGER,
                    value_classification TEXT
                )
            """).format(sql.Identifier(table_name)))
            conn.commit()
            logger.info(f"Table '{table_name}' verified/created for F&G Index.")
    except psycopg2.Error as e:
        logger.error(f"Error creating F&G Index table '{table_name}': {e}")
        conn.rollback()


def save_fng_to_db(data: List[Dict[str, Any]], table_name: str):
    """Saves a list of Fear and Greed Index data to PostgreSQL database."""
    conn = create_connection()
    if not conn:
        return
        
    try:
        create_fng_table(conn, table_name)
        
        rows = [
            (int(item['timestamp']) * 1000, int(item['value']), item['value_classification'])
            for item in data
        ]
        
        with conn.cursor() as cursor:
            insert_query = sql.SQL("""
                INSERT INTO {} (timestamp, value, value_classification)
                VALUES %s
                ON CONFLICT (timestamp) DO NOTHING
            """).format(sql.Identifier(table_name))
            extras.execute_values(cursor, insert_query, rows)
            
        conn.commit()
        logger.info(f"F&G Index data saved to table '{table_name}'.")
    except psycopg2.Error as e:
        logger.error(f"Error saving F&G Index data: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


def get_last_fng_timestamp_from_db(table_name: str) -> Optional[int]:
    """Gets the timestamp of the last F&G Index entry saved in the database."""
    conn = create_connection()
    if not conn:
        return None
        
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("SELECT MAX(timestamp) FROM {}").format(sql.Identifier(table_name)))
            result = cursor.fetchone()
            last_timestamp_ms = result[0] if result else None
            if last_timestamp_ms:
                return (last_timestamp_ms // 1000) + (24 * 60 * 60)
            return None
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == "42P01":
            logger.warning(f"Table '{table_name}' does not exist yet. Starting fresh.")
            return None
        logger.error(f"Error fetching last F&G timestamp: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_fng_data_from_db(table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
    """Loads Fear and Greed Index data from PostgreSQL to a Pandas DataFrame."""
    conn = create_connection()
    if not conn:
        return pd.DataFrame()
        
    try:
        with conn.cursor() as cursor:
            if limit:
                query = sql.SQL("SELECT * FROM {} ORDER BY timestamp ASC LIMIT %s").format(sql.Identifier(table_name))
                cursor.execute(query, (limit,))
            else:
                query = sql.SQL("SELECT * FROM {} ORDER BY timestamp ASC").format(sql.Identifier(table_name))
                cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.columns = [col.replace('_', ' ').title().replace(' ', '_') for col in df.columns]
        
        return df
    except psycopg2.Error as e:
        logger.error(f"Error loading F&G Index data: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


# ==================== ON-CHAIN DATA TABLE ====================

def create_on_chain_table(conn: PGConnection, table_name: str):
    """Creates a table to store on-chain data."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    timestamp BIGINT PRIMARY KEY,
                    transactions_24h INTEGER,
                    fees_usd_24h DOUBLE PRECISION
                )
            """).format(sql.Identifier(table_name)))
            conn.commit()
            logger.info(f"Table '{table_name}' verified/created for on-chain data.")
    except psycopg2.Error as e:
        logger.error(f"Error creating on-chain table '{table_name}': {e}")
        conn.rollback()


def save_on_chain_to_db(data: Dict[str, Any], table_name: str):
    """Saves on-chain data to PostgreSQL database."""
    conn = create_connection()
    if not conn:
        return
        
    try:
        create_on_chain_table(conn, table_name)
        
        import time
        timestamp_ms = int(time.time() * 1000)
        
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
                INSERT INTO {} (timestamp, transactions_24h, fees_usd_24h)
                VALUES (%s, %s, %s)
                ON CONFLICT (timestamp) DO NOTHING
            """).format(sql.Identifier(table_name)),
            (timestamp_ms, data.get('transactions_24h'), data.get('average_transaction_fee_usd_24h')))
            
        conn.commit()
        logger.info(f"On-chain data saved to table '{table_name}'.")
    except psycopg2.Error as e:
        logger.error(f"Error saving on-chain data: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


# ==================== IMPLIED VOLATILITY TABLE ====================

def create_implied_volatility_table(conn: PGConnection, table_name: str):
    """Creates a table to store implied volatility data from Deribit."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    timestamp BIGINT PRIMARY KEY,
                    volatility DOUBLE PRECISION
                )
            """).format(sql.Identifier(table_name)))
            conn.commit()
            logger.info(f"Table '{table_name}' verified/created for Implied Volatility.")
    except psycopg2.Error as e:
        logger.error(f"Error creating Implied Volatility table '{table_name}': {e}")
        conn.rollback()


def save_implied_volatility_to_db(data: List[Dict[str, Any]], table_name: str):
    """Saves a list of implied volatility data to PostgreSQL database."""
    conn = create_connection()
    if not conn:
        return
        
    try:
        create_implied_volatility_table(conn, table_name)
        
        rows = [(int(item.get('timestamp')), float(item.get('volatility'))) for item in data]
        
        with conn.cursor() as cursor:
            insert_query = sql.SQL("""
                INSERT INTO {} (timestamp, volatility)
                VALUES %s
                ON CONFLICT (timestamp) DO NOTHING
            """).format(sql.Identifier(table_name))
            extras.execute_values(cursor, insert_query, rows)
            
        conn.commit()
        logger.info(f"Implied Volatility data saved to table '{table_name}'.")
    except psycopg2.Error as e:
        logger.error(f"Error saving Implied Volatility data: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


def get_last_implied_volatility_timestamp_from_db(table_name: str) -> Optional[int]:
    """Returns the next timestamp (ms) to be fetched for Implied Volatility, or None."""
    conn = create_connection()
    if not conn:
        return None
        
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("SELECT MAX(timestamp) FROM {}").format(sql.Identifier(table_name)))
            result = cursor.fetchone()
            last_ts = result[0] if result else None
            if last_ts:
                return last_ts + 1
            return None
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == "42P01":
            logger.warning(f"Table '{table_name}' does not exist yet. Starting fresh.")
            return None
        logger.error(f"Error fetching last Implied Volatility timestamp: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_implied_volatility_data_from_db(table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
    """Loads Implied Volatility data to a DataFrame ordered by timestamp asc."""
    conn = create_connection()
    if not conn:
        return pd.DataFrame()
        
    try:
        with conn.cursor() as cursor:
            if limit:
                query = sql.SQL("SELECT * FROM {} ORDER BY timestamp ASC LIMIT %s").format(sql.Identifier(table_name))
                cursor.execute(query, (limit,))
            else:
                query = sql.SQL("SELECT * FROM {} ORDER BY timestamp ASC").format(sql.Identifier(table_name))
                cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.columns = [col.replace('_', ' ').title().replace(' ', '_') for col in df.columns]
        
        return df
    except Exception as e:
        logger.debug(f"Error loading Implied Volatility data (maybe table missing): {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


# ==================== UNISWAP POOL DATA TABLE ====================

def create_uniswap_pool_table(conn: PGConnection, table_name: str):
    """Creates a table to store Uniswap poolDayData (volumeUSD and tvlUSD per day)."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    timestamp BIGINT PRIMARY KEY,
                    volume_usd DOUBLE PRECISION,
                    tvl_usd DOUBLE PRECISION
                )
            """).format(sql.Identifier(table_name)))
            conn.commit()
            logger.info(f"Table '{table_name}' verified/created for Uniswap Pool Data.")
    except psycopg2.Error as e:
        logger.error(f"Error creating Uniswap Pool table '{table_name}': {e}")
        conn.rollback()


def save_uniswap_pool_data_to_db(data: List[Dict[str, Any]], table_name: str):
    """Saves a list of Uniswap pool data with keys timestamp (ms), volumeUSD, tvlUSD."""
    conn = create_connection()
    if not conn:
        return
        
    try:
        create_uniswap_pool_table(conn, table_name)
        
        rows = [
            (int(item.get('timestamp')), 
             float(item.get('volumeUSD') or 0.0),
             float(item.get('tvlUSD') or item.get('tvl') or 0.0))
            for item in data
        ]
        
        with conn.cursor() as cursor:
            insert_query = sql.SQL("""
                INSERT INTO {} (timestamp, volume_usd, tvl_usd)
                VALUES %s
                ON CONFLICT (timestamp) DO NOTHING
            """).format(sql.Identifier(table_name))
            extras.execute_values(cursor, insert_query, rows)
            
        conn.commit()
        logger.info(f"Uniswap data saved to table '{table_name}'.")
    except psycopg2.Error as e:
        logger.error(f"Error saving Uniswap data: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


def get_last_uniswap_timestamp_from_db(table_name: str) -> Optional[int]:
    """Gets the last timestamp from Uniswap Pool Data table."""
    conn = create_connection()
    if not conn:
        return None
        
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql.SQL("SELECT MAX(timestamp) FROM {}").format(sql.Identifier(table_name)))
            result = cursor.fetchone()
            last_ts = result[0] if result else None
            if last_ts:
                return last_ts + 1
            return None
    except psycopg2.Error as e:
        if getattr(e, "pgcode", None) == "42P01":
            logger.warning(f"Table '{table_name}' does not exist yet. Starting fresh.")
            return None
        logger.error(f"Error fetching last Uniswap Pool timestamp: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_uniswap_pool_data_from_db(table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
    """Loads Uniswap pool data to a DataFrame."""
    conn = create_connection()
    if not conn:
        return pd.DataFrame()
        
    try:
        with conn.cursor() as cursor:
            if limit:
                query = sql.SQL("SELECT * FROM {} ORDER BY timestamp ASC LIMIT %s").format(sql.Identifier(table_name))
                cursor.execute(query, (limit,))
            else:
                query = sql.SQL("SELECT * FROM {} ORDER BY timestamp ASC").format(sql.Identifier(table_name))
                cursor.execute(query)
            
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            # Rename to match expected format
            df.rename(columns={'volume_usd': 'VolumeUSD', 'tvl_usd': 'TVL_USD', 'timestamp': 'Timestamp'}, inplace=True)
        
        return df
    except Exception as e:
        logger.debug(f"Error loading Uniswap data (maybe table missing): {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()
