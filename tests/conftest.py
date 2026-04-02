import os
import pytest
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
import pandas as pd

import backend.src.config as config
from backend.src.data import storage

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    TEST_DATABASE_URL = "postgresql://user:password@postgres_test:5432/defisys_test"
    os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL

# Capture the original main DB URL before overriding
MAIN_DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@postgres:5432/defisys")

@pytest.fixture(scope="session", autouse=True)
def override_database_url():
    """
    Override the DATABASE_URL with TEST_DATABASE_URL for all tests.
    This ensures tests never run against the production database.
    """
    # Override module-level constants
    config.DATABASE_URL = TEST_DATABASE_URL
    config._settings.DATABASE_URL = TEST_DATABASE_URL
    storage.DATABASE_URL = TEST_DATABASE_URL
    
    # Also update the environment variable
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    
    # Populate the test database with a minimal dataset (last 7 days)
    # from the main database to speed up tests.
    _populate_test_db()
    
    yield

def _populate_test_db():
    """
    Copies the last 7 days (42 candles of 4h) of BTCUSDT from the main DB to the test DB.
    """
    try:
        # 1. Connect to main DB and fetch data
        conn_main = psycopg2.connect(MAIN_DATABASE_URL)
        query = 'SELECT * FROM "klines_BTCUSDT_4h" ORDER BY open_time DESC LIMIT 42'
        try:
            # Filter warnings for pd.read_sql since we pass a connection instead of engine
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                df = pd.read_sql(query, conn_main)
        except Exception as e:
            # Table might not exist yet if main DB is fresh
            df = pd.DataFrame()
            print(f"Warning: Could not fetch from main DB: {e}")
        finally:
            conn_main.close()
        
        if not df.empty:
            df = df.sort_values("open_time", ascending=True)
            
            # 2. Connect to test DB and insert
            conn_test = psycopg2.connect(TEST_DATABASE_URL)
            conn_test.autocommit = True
            
            with conn_test.cursor() as cur:
                # Create table if it doesn't exist (using storage function)
                storage.create_klines_table(conn_test, "klines_BTCUSDT_4h")
                
                # Clear existing data in test klines
                cur.execute('TRUNCATE TABLE "klines_BTCUSDT_4h" CASCADE')
                
                # Insert the data
                cols = df.columns.tolist()
                vals = [tuple(x) for x in df.values]
                insert_query = sql.SQL("INSERT INTO \"klines_BTCUSDT_4h\" ({}) VALUES %s ON CONFLICT (open_time) DO NOTHING").format(
                    sql.SQL(', ').join(map(sql.Identifier, cols))
                )
                execute_values(cur, insert_query, vals)
            
            conn_test.close()
            print(f"\n[Test Setup] Populated test DB with {len(df)} klines.")
    except Exception as e:
        print(f"\n[Test Setup] Warning: Failed to populate test db: {e}")


@pytest.fixture(scope="function", autouse=True)
def clean_test_db():
    """
    Cleans transaction tables between tests to ensure complete isolation.
    Leaves the klines table intact.
    """
    try:
        conn = psycopg2.connect(TEST_DATABASE_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            tables = [
                "positions_log", 
                "trades", 
                "ml_predictions", 
                "simulation_summary"
            ]
            for table in tables:
                try:
                    cur.execute(sql.SQL("TRUNCATE TABLE {} CASCADE").format(sql.Identifier(table)))
                except psycopg2.Error:
                    pass  # Table might not exist
        conn.close()
    except Exception as e:
        print(f"\n[Test Setup] Warning: Failed to clean test db tables: {e}")