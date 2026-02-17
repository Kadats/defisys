"""
PostgreSQL Storage Layer - Handles all database operations.

This module replaces the SQLite database.py with PostgreSQL-specific implementations.
Uses psycopg2 for database connectivity and implements proper PostgreSQL schemas.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List
import psycopg2
from psycopg2 import sql, extras
from psycopg2.extensions import connection as PGConnection
import pandas as pd

from backend.src.config import DATABASE_URL

logger = logging.getLogger(__name__)


def create_connection() -> Optional[PGConnection]:
    """Creates a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
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


# ==================== POSITIONS LOG TABLE ====================

def create_positions_log_table(conn: PGConnection):
    """Creates the 'positions_log' table to track opened and closed LPs."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions_log (
                    id SERIAL PRIMARY KEY,
                    open_timestamp BIGINT NOT NULL,
                    close_timestamp BIGINT,
                    strategy_used TEXT,
                    capital_allocated_usd DOUBLE PRECISION,
                    open_price DOUBLE PRECISION,
                    close_price DOUBLE PRECISION,
                    range_lower DOUBLE PRECISION,
                    range_upper DOUBLE PRECISION,
                    final_profit_usd DOUBLE PRECISION
                )
            """)
            conn.commit()
            logger.info("Table 'positions_log' verified/created successfully.")
    except psycopg2.Error as e:
        logger.error(f"Error creating 'positions_log' table: {e}")
        conn.rollback()


def log_open_position(open_timestamp: int, strategy: str, capital_usd: float, 
                     open_price: float, range_lower: float, range_upper: float) -> Optional[int]:
    """
    Records a new opened LP in the database and returns the position ID.
    """
    conn = create_connection()
    if not conn:
        return None
        
    try:
        create_positions_log_table(conn)
        
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO positions_log (open_timestamp, strategy_used, capital_allocated_usd, 
                                         open_price, range_lower, range_upper)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (open_timestamp, strategy, capital_usd, open_price, range_lower, range_upper))
            
            position_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"New position {position_id} registered in 'positions_log'.")
            return position_id
            
    except psycopg2.Error as e:
        logger.error(f"Error registering position opening in DB: {e}")
        conn.rollback()
        return None
    finally:
        if conn:
            conn.close()


def log_close_position(position_id: int, close_timestamp: int, close_price: float, final_profit: float):
    """Updates an existing position with closing data and profit."""
    conn = create_connection()
    if not conn:
        return
        
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE positions_log
                SET close_timestamp = %s,
                    close_price = %s,
                    final_profit_usd = %s
                WHERE id = %s
            """, (close_timestamp, close_price, final_profit, position_id))
            
        conn.commit()
        logger.info(f"Position {position_id} updated with closing data.")
        
    except psycopg2.Error as e:
        logger.error(f"Error registering position closing in DB: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


# ==================== TRADES TABLE ====================

def create_trades_table(conn: PGConnection):
    """Creates the 'trades' table to store all transaction log data."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    action TEXT NOT NULL,
                    btc_price DOUBLE PRECISION NOT NULL,
                    usd_amount DOUBLE PRECISION DEFAULT 0.0,
                    btc_amount DOUBLE PRECISION DEFAULT 0.0,
                    fee_usd DOUBLE PRECISION DEFAULT 0.0,
                    pnl_usd DOUBLE PRECISION DEFAULT 0.0,
                    details TEXT
                )
            """)
            conn.commit()
            logger.info("Table 'trades' verified/created successfully.")
    except psycopg2.Error as e:
        logger.error(f"Error creating 'trades' table: {e}")
        conn.rollback()


def save_trades(trades_list: list, current_price: float = 0.0):
    """
    Salva a lista de trades (transaction_log) no banco de dados.
    Calcula PnL flutuante para posições abertas (Buy Only).
    Limpa os dados antigos antes de inserir os novos.
    
    Args:
        trades_list: Lista de dicionários contendo os dados das transações.
                     Cada dicionário deve ter: timestamp, action, btc_price, 
                     usd_amount, btc_amount, fee_usd, pnl_usd, details
        current_price: Preço atual do BTC para calcular PnL flutuante de posições abertas.
                      Se 0 ou não fornecido, usa o último preço do histórico.
    """
    conn = create_connection()
    if not conn:
        logger.error("Não foi possível conectar ao banco de dados para salvar trades.")
        return
    
    try:
        create_trades_table(conn)
        
        # Limpar trades antigos
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM trades")
            logger.info("Trades antigos removidos da tabela 'trades'.")
        
        # Inserir novos trades
        if not trades_list:
            logger.info("Nenhum trade para salvar.")
            conn.commit()
            return
        
        # Processa cada trade, calculando PnL flutuante para posições abertas
        trades_to_save = []
        for trade in trades_list:
            trade_copy = trade.copy()
            
            # V18: QUANTITATIVE REFINEMENT - Calcular PnL virtual para posições abertas
            # Posições abertas são identificadas por ações de compra sem venda correspondente
            is_buy_action = trade_copy.get("action", "") in ["BUY_HODL", "BUY"]
            btc_amount = float(trade_copy.get("btc_amount", 0))
            entry_price = float(trade_copy.get("btc_price", 0))
            
            # Se é uma posição aberta (compra com BTC > 0) e temos preço atual válido
            if is_buy_action and btc_amount > 0 and entry_price > 0 and current_price > 0:
                # Calcular PnL virtual usando preço atual como "exit_price virtual"
                # PnL = (Preço Atual - Preço de Entrada) × Quantidade
                virtual_pnl_usd = (current_price - entry_price) * btc_amount
                
                # Calcular ROI: (PnL / Capital Investido) × 100%
                capital_invested = entry_price * btc_amount
                virtual_roi_percent = (virtual_pnl_usd / capital_invested * 100) if capital_invested > 0 else 0
                
                # Atualizar o PnL no trade (sem alterar o banco para trades fechados)
                trade_copy["pnl_usd"] = virtual_pnl_usd
                
                # Adicionar tag [OPEN POSITION] nos detalhes para identificação visual
                details = trade_copy.get("details", "")
                if "[OPEN POSITION]" not in details:
                    trade_copy["details"] = (
                        f"[OPEN POSITION] Entry: ${entry_price:.2f} | "
                        f"Current: ${current_price:.2f} | "
                        f"Virtual ROI: {virtual_roi_percent:+.2f}% | {details}"
                    ).strip()
                
                logger.info(
                    f"💼 Virtual PnL calculated: {trade_copy.get('action')} - "
                    f"Entry ${entry_price:.2f} → Current ${current_price:.2f}, "
                    f"Amount {btc_amount:.6f} BTC, PnL ${virtual_pnl_usd:+.2f} (ROI: {virtual_roi_percent:+.2f}%)"
                )
            
            trades_to_save.append(trade_copy)
        
        with conn.cursor() as cursor:
            for trade in trades_to_save:
                # Converter timestamp para formato PostgreSQL
                timestamp = trade.get("timestamp")
                if isinstance(timestamp, pd.Timestamp):
                    timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                elif hasattr(timestamp, 'isoformat'):
                    timestamp_str = timestamp.isoformat()
                else:
                    timestamp_str = str(timestamp)
                
                cursor.execute("""
                    INSERT INTO trades (timestamp, action, btc_price, usd_amount, 
                                      btc_amount, fee_usd, pnl_usd, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    timestamp_str,
                    trade.get("action", ""),
                    float(trade.get("btc_price", 0)),
                    float(trade.get("usd_amount", 0)),
                    float(trade.get("btc_amount", 0)),
                    float(trade.get("fee_usd", 0)),
                    float(trade.get("pnl_usd", 0)),
                    trade.get("details", "")
                ))
        
        conn.commit()
        logger.info(f"{len(trades_to_save)} trades salvos com sucesso na tabela 'trades'.")
        
    except psycopg2.Error as e:
        logger.error(f"Erro ao salvar trades no banco de dados: {e}")
        conn.rollback()
    except Exception as e:
        logger.error(f"Erro inesperado ao salvar trades: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


# ==================== ML PREDICTIONS TABLE ====================

def create_ml_predictions_table(conn: PGConnection):
    """Creates the 'ml_predictions' table to store model results."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ml_predictions (
                    open_time TIMESTAMP PRIMARY KEY,
                    prediction INTEGER,
                    prediction_proba FLOAT,
                    prediction_correct BOOLEAN
                )
            """)
            conn.commit()
            logger.info("Table 'ml_predictions' verified/created successfully.")
    except psycopg2.Error as e:
        logger.error(f"Error creating 'ml_predictions' table: {e}")
        conn.rollback()


def save_predictions_to_db(df: pd.DataFrame):
    """
    Saves model predictions to the database.
    Deletes old data and inserts new predictions.
    """
    conn = create_connection()
    if not conn:
        return
        
    try:
        create_ml_predictions_table(conn)
        
        df_to_save = df.copy()
        # Keep only needed columns early (including prediction_proba)
        df_to_save = df_to_save[['Open_time', 'prediction', 'prediction_proba', 'prediction_correct']].copy()
        
        # Drop rows without a prediction (ensure we only save actual model outputs)
        df_to_save = df_to_save[df_to_save['prediction'].notna()]
        
        # Fill NaNs with sentinel -1 for robustness in DB INTEGER columns
        # Convert to numeric first to coerce any non-numeric values
        df_to_save['prediction'] = pd.to_numeric(df_to_save['prediction'], errors='coerce')
        df_to_save['prediction_proba'] = pd.to_numeric(df_to_save['prediction_proba'], errors='coerce')
        df_to_save['prediction_correct'] = pd.to_numeric(df_to_save['prediction_correct'], errors='coerce')
        df_to_save[['prediction', 'prediction_correct']] = df_to_save[['prediction', 'prediction_correct']].fillna(-1)
        df_to_save['prediction_proba'] = df_to_save['prediction_proba'].fillna(0.0)
        
        # Enforce native Python int types for DB insertion
        df_to_save['prediction'] = df_to_save['prediction'].astype(int)
        df_to_save['prediction_correct'] = df_to_save['prediction_correct'].astype(bool)
        
        # Convert Open_time from pandas datetime to proper format for PostgreSQL
        # Ensure it's a pandas datetime first
        if not pd.api.types.is_datetime64_any_dtype(df_to_save['Open_time']):
            df_to_save['Open_time'] = pd.to_datetime(df_to_save['Open_time'])
        
        # Prepare rows for insert - convert datetime to ISO string for PostgreSQL
        rows = [
            (row['Open_time'].isoformat() if hasattr(row['Open_time'], 'isoformat') else str(row['Open_time']), 
             int(row['prediction']), 
             float(row['prediction_proba']), 
             bool(row['prediction_correct']))
            for _, row in df_to_save.iterrows()
        ]
        logger.info(f"Preparing to insert {len(rows)} rows into 'ml_predictions'...")
        
        # DEBUG: Check first row type
        if rows:
            logger.info(f"DEBUG: First row types: {[type(x) for x in rows[0]]}")
            logger.info(f"DEBUG: First row values: {rows[0]}")
        
        # Delete old predictions and insert new ones
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM ml_predictions")
            
            # Use parameterized query with proper type casting for timestamp
            insert_query = """
                INSERT INTO ml_predictions (open_time, prediction, prediction_proba, prediction_correct)
                VALUES %s
                ON CONFLICT (open_time) DO UPDATE SET
                    prediction = EXCLUDED.prediction,
                    prediction_proba = EXCLUDED.prediction_proba,
                    prediction_correct = EXCLUDED.prediction_correct
            """
            if rows:
                # execute_values replaces %s with the template
                extras.execute_values(
                    cursor, 
                    insert_query, 
                    rows,
                    template="(CAST(%s AS timestamp), %s, %s, %s)"
                )
            else:
                logger.warning("No rows to insert for 'ml_predictions'. Skipping insert.")
            
        conn.commit()
        logger.info(f"{len(rows)} predictions saved to 'ml_predictions' table.")
        
    except Exception as e:
        logger.error(f"Error saving predictions to DB: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


# ==================== SIMULATION ====================
def clear_simulation_data():
    """Limpa as tabelas de simulação para evitar dados duplicados."""
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Apaga todos os registros de logs de posição
            cursor.execute("DELETE FROM positions_log")
            # Apaga todos os registros de trades
            cursor.execute("DELETE FROM trades")
            conn.commit()
            print("🧹 Dados de simulação anteriores limpos com sucesso.")
        except Exception as e:
            print(f"Erro ao limpar dados: {e}")
        finally:
            conn.close()