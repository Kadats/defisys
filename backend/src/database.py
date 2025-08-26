import sqlite3
import pandas as pd
import os
import time
import logging

from .config import DB_FILE # Importa o caminho do DB do config

logger = logging.getLogger(__name__)

def create_connection(db_file: str = DB_FILE):
    """Cria uma conexão com o banco de dados SQLite especificado."""
    conn = None
    try:
        # Garante que o diretório do DB exista antes de tentar criar o arquivo
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        logger.error("Erro ao conectar ao banco de dados SQLite: %s", e)
    return conn

# Tabela Binance
def create_table(conn: sqlite3.Connection, table_name: str):
    """Cria uma tabela para armazenar os dados OHLCV se ela não existir."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                Open_time INTEGER PRIMARY KEY,
                Open REAL,
                High REAL,
                Low REAL,
                Close REAL,
                Volume REAL,
                Close_time INTEGER,
                Quote_asset_volume REAL,
                Number_of_trades INTEGER,
                Taker_buy_base_asset_volume REAL,
                Taker_buy_quote_asset_volume REAL
            )
        """)
        conn.commit()
        logger.info("Tabela '%s' verificada/criada com sucesso.", table_name)
    except sqlite3.Error as e:
        logger.error("Erro ao criar tabela '%s': %s", table_name, e)

def save_klines_to_db(df: pd.DataFrame, table_name: str, db_file: str = DB_FILE):
    """Salva um DataFrame de klines em um banco de dados SQLite."""
    conn = create_connection(db_file)
    if conn:
        try:
            create_table(conn, table_name) # Chame a função create_table corretamente

            df_to_save = df.copy()

            # Converte objetos datetime para timestamps INTEIROS em MILISSEGUNDOS para o SQLite
            # O .values.astype(np.int64) converte para nanosegundos, depois dividimos por 1 milhão (10**6) para milissegundos.
            df_to_save['Open_time'] = (df_to_save['Open_time'].values.astype(int) // 10**6).astype(int)
            df_to_save['Close_time'] = (df_to_save['Close_time'].values.astype(int) // 10**6).astype(int)

            # Ajusta nomes de colunas para SQLite (removendo espaços)
            df_to_save.columns = [col.replace(' ', '_') for col in df_to_save.columns]

            df_to_save.to_sql(table_name, conn, if_exists='append', index=False)
            logger.info("Dados salvos/atualizados na tabela '%s' em '%s'", table_name, db_file)
        except sqlite3.IntegrityError:
            logger.warning("Alguns dados já existem (Open_time duplicado), pulando inserção.")
        except sqlite3.Error as e:
            logger.error("Erro ao salvar dados no banco de dados: %s", e)
        finally:
            conn.close()

def get_last_timestamp_from_db(table_name: str, db_file: str = DB_FILE) -> int:
    """Obtém o timestamp da última vela salva no banco de dados."""
    conn = create_connection(db_file)
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT MAX(Open_time) FROM {table_name}")
            last_timestamp = cursor.fetchone()[0]
            if last_timestamp:
                return last_timestamp + 1 # Retorna o próximo timestamp a buscar (o início da próxima vela)
            return None
        except sqlite3.Error as e:
            logger.error("Erro ao buscar último timestamp da tabela '%s': %s", table_name, e)
            return None
        finally:
            conn.close()
    return None

def get_data_from_db(table_name: str, db_file: str = DB_FILE, limit: int = None) -> pd.DataFrame:
    """Carrega dados de uma tabela SQLite para um DataFrame Pandas."""
    conn = create_connection(db_file)
    if conn:
        try:
            query = f"SELECT * FROM {table_name} ORDER BY Open_time ASC"
            if limit:
                query += f" LIMIT {limit}"
                        
            df = pd.read_sql(query, conn) 
            
            # Faça a conversão para datetime APÓS ler o DataFrame
            if not df.empty:
                df['Open_time'] = pd.to_datetime(df['Open_time'], unit='ms')
                df['Close_time'] = pd.to_datetime(df['Close_time'], unit='ms')
            
            return df
        except sqlite3.Error as e:
            logger.error("Erro ao carregar dados do banco de dados: %s", e)
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()

#Tabela Binance Open Interest
def create_open_interest_table(conn: sqlite3.Connection, table_name: str):
    """Cria uma tabela para armazenar o histórico de Open Interest."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                Timestamp INTEGER PRIMARY KEY,
                Symbol TEXT,
                OpenInterest REAL
            )
        """)
        conn.commit()
        logger.info("Tabela '%s' verificada/criada com sucesso para Open Interest.", table_name)
    except sqlite3.Error as e:
        logger.error("Erro ao criar tabela '%s' para Open Interest: %s", table_name, e)

def save_open_interest_to_db(data: dict, table_name: str, db_file: str):
    """Salva um dado de Open Interest em um banco de dados SQLite."""
    conn = create_connection(db_file)
    if conn:
        try:
            create_open_interest_table(conn, table_name)
            cursor = conn.cursor()
            
            # O timestamp da API já é em milissegundos
            row = (data['time'], data['symbol'], float(data['openInterest']))
            
            cursor.execute(f"""
                INSERT OR IGNORE INTO {table_name} (Timestamp, Symbol, OpenInterest)
                VALUES (?, ?, ?)
            """, row)
            conn.commit()
            logger.info("Dados de Open Interest salvos/atualizados na tabela '%s'.", table_name)
        except sqlite3.Error as e:
            logger.error("Erro ao salvar dados de Open Interest no banco de dados: %s", e)
        finally:
            conn.close()

# Tabela Binance Funding Rate
def create_funding_rate_table(conn: sqlite3.Connection, table_name: str):
    """Cria uma tabela para armazenar o histórico de Funding Rate."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                FundingTime INTEGER PRIMARY KEY,
                Symbol TEXT,
                FundingRate REAL
            )
        """)
        conn.commit()
        logger.info("Tabela '%s' verificada/criada com sucesso para Funding Rate.", table_name)
    except sqlite3.Error as e:
        logger.error("Erro ao criar tabela '%s' para Funding Rate: %s", table_name, e)

def save_funding_rate_to_db(data: list, table_name: str, db_file: str):
    """Salva uma lista de dados de Funding Rate em um banco de dados SQLite."""
    conn = create_connection(db_file)
    if conn:
        try:
            create_funding_rate_table(conn, table_name)
            cursor = conn.cursor()
            
            rows = [(item['fundingTime'], item['symbol'], float(item['fundingRate'])) for item in data]
            
            cursor.executemany(f"""
                INSERT OR IGNORE INTO {table_name} (FundingTime, Symbol, FundingRate)
                VALUES (?, ?, ?)
            """, rows)
            conn.commit()
            logger.info("Dados de Funding Rate salvos/atualizados na tabela '%s'.", table_name)
        except sqlite3.Error as e:
            logger.error("Erro ao salvar dados de Funding Rate no banco de dados: %s", e)
        finally:
            conn.close()

       
# Tabela Fear and Greed (F&G) Index
def create_fng_table(conn: sqlite3.Connection, table_name: str):
    """Cria uma tabela para armazenar os dados do Fear and Greed Index."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                Timestamp INTEGER PRIMARY KEY,
                Value INTEGER,
                Value_classification TEXT
            )
        """)
        conn.commit()
        logger.info("Tabela '%s' verificada/criada com sucesso para F&G Index.", table_name)
    except sqlite3.Error as e:
        logger.error("Erro ao criar tabela '%s' para F&G Index: %s", table_name, e)

def save_fng_to_db(data: list, table_name: str, db_file: str):
    """Salva uma lista de dicionários de dados do F&G Index em um banco de dados SQLite."""
    conn = create_connection(db_file)
    if conn:
        try:
            create_fng_table(conn, table_name)
            cursor = conn.cursor()
            
            # Prepara os dados para inserção
            rows = []
            for item in data:
                # O timestamp da API do F&G já é em segundos
                timestamp_ms = int(item['timestamp']) * 1000 # Convertemos para ms para consistência com velas
                rows.append((timestamp_ms, int(item['value']), item['value_classification']))
            
            # Insere ou ignora se já existe (devido ao PRIMARY KEY)
            cursor.executemany(f"""
                INSERT OR IGNORE INTO {table_name} (Timestamp, Value, Value_classification)
                VALUES (?, ?, ?)
            """, rows)
            conn.commit()
            logger.info("Dados do F&G Index salvos/atualizados na tabela '%s'.", table_name)
        except sqlite3.Error as e:
            logger.error("Erro ao salvar dados do F&G Index no banco de dados: %s", e)
        finally:
            conn.close()

def get_last_fng_timestamp_from_db(table_name: str, db_file: str) -> int:
    """Obtém o timestamp da última entrada do F&G Index salva no banco de dados."""
    conn = create_connection(db_file)
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT MAX(Timestamp) FROM {table_name}")
            last_timestamp_ms = cursor.fetchone()[0]
            if last_timestamp_ms:
                # Retornamos o próximo timestamp a buscar (em segundos, pois a API FNG espera isso)
                return (last_timestamp_ms // 1000) + (24 * 60 * 60) # Pega o próximo dia (em segundos)
            return None
        except sqlite3.Error as e:
            logger.error("Erro ao buscar último timestamp do F&G Index: %s", e)
            return None
        finally:
            conn.close()
    return None

def get_fng_data_from_db(table_name: str, db_file: str, limit: int = None) -> pd.DataFrame:
    """Carrega dados do F&G Index de uma tabela SQLite para um DataFrame Pandas."""
    conn = create_connection(db_file)
    if conn:
        try:
            query = f"SELECT * FROM {table_name} ORDER BY Timestamp ASC"
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql(query, conn) 
            
            if not df.empty:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
            
            return df
        except sqlite3.Error as e:
            logger.error("Erro ao carregar dados do F&G Index: %s", e)
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()


# Tabela On-Chain Blockchair Bitcoin
def create_on_chain_table(conn: sqlite3.Connection, table_name: str):
    """Cria uma tabela para armazenar dados on-chain."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                Timestamp INTEGER PRIMARY KEY,
                Transactions_24h INTEGER,
                Fees_usd_24h REAL
            )
        """)
        conn.commit()
        logger.info("Tabela '%s' verificada/criada com sucesso para dados on-chain.", table_name)
    except sqlite3.Error as e:
        logger.error("Erro ao criar tabela '%s' para dados on-chain: %s", table_name, e)

def save_on_chain_to_db(data: dict, table_name: str, db_file: str):
    """Salva dados on-chain em um banco de dados SQLite."""
    conn = create_connection(db_file)
    if conn:
        try:
            create_on_chain_table(conn, table_name)
            cursor = conn.cursor()
            
            # A API da Blockchair não fornece histórico fácil, então pegaremos o estado atual
            # e usaremos o timestamp de agora para salvar.
            timestamp_ms = int(time.time() * 1000)
            
            row = (
                timestamp_ms,
                data.get('transactions_24h'),
                data.get('average_transaction_fee_usd_24h')
            )
            
            # Usamos INSERT OR IGNORE para evitar duplicatas se rodarmos mais de uma vez no mesmo dia
            cursor.execute(f"""
                INSERT OR IGNORE INTO {table_name} (Timestamp, Transactions_24h, Fees_usd_24h)
                VALUES (?, ?, ?)
            """, row)
            conn.commit()
            logger.info("Dados on-chain salvos/atualizados na tabela '%s'.", table_name)
        except sqlite3.Error as e:
            logger.error("Erro ao salvar dados on-chain no banco de dados: %s", e)
        finally:
            conn.close()


# Tabela Implied Volatility (Deribit)
def create_implied_volatility_table(conn: sqlite3.Connection, table_name: str):
    """Cria a tabela para armazenar a volatilidade implícita obtida da Deribit."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                Timestamp INTEGER PRIMARY KEY,
                Volatility REAL
            )
        """)
        conn.commit()
        logger.info("Tabela '%s' verificada/criada com sucesso para Implied Volatility.", table_name)
    except sqlite3.Error as e:
        logger.error("Erro ao criar tabela '%s' para Implied Volatility: %s", table_name, e)


def save_implied_volatility_to_db(data: list, table_name: str, db_file: str):
    """Salva uma lista de dicionários de volatilidade implícita no banco de dados.

    Cada item em `data` deve ter as chaves: 'timestamp' (ms) e 'volatility' (float).
    """
    conn = create_connection(db_file)
    if conn:
        try:
            create_implied_volatility_table(conn, table_name)
            cursor = conn.cursor()

            rows = []
            for item in data:
                # espera timestamp em ms
                ts = int(item.get('timestamp'))
                vol = float(item.get('volatility'))
                rows.append((ts, vol))

            cursor.executemany(f"""
                INSERT OR IGNORE INTO {table_name} (Timestamp, Volatility)
                VALUES (?, ?)
            """, rows)
            conn.commit()
            logger.info("Dados de Implied Volatility salvos/atualizados na tabela '%s'.", table_name)
        except sqlite3.Error as e:
            logger.error("Erro ao salvar Implied Volatility no banco de dados: %s", e)
        finally:
            conn.close()


def get_last_implied_volatility_timestamp_from_db(table_name: str, db_file: str) -> int:
    """Retorna o próximo timestamp (ms) a ser buscado para Implied Volatility, ou None."""
    conn = create_connection(db_file)
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT MAX(Timestamp) FROM {table_name}")
            last_ts = cursor.fetchone()[0]
            if last_ts:
                return last_ts + 1
            return None
        except sqlite3.Error as e:
            logger.error("Erro ao buscar último timestamp de Implied Volatility: %s", e)
            return None
        finally:
            conn.close()
    return None


def get_implied_volatility_data_from_db(table_name: str, db_file: str, limit: int = None) -> pd.DataFrame:
    """Carrega dados de Implied Volatility para um DataFrame ordenado por Timestamp asc."""
    conn = create_connection(db_file)
    if conn:
        try:
            query = f"SELECT * FROM {table_name} ORDER BY Timestamp ASC"
            if limit:
                query += f" LIMIT {limit}"

            df = pd.read_sql(query, conn)
            if not df.empty:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
            return df
        except Exception as e:
            # If the table does not exist or another DB error occurs, return an empty DataFrame; caller will handle
            logger.debug("Erro ao carregar dados de Implied Volatility (talvez tabela ausente): %s", e)
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()

