import logging
from typing import Optional
from psycopg2.extensions import connection as PGConnection

logger = logging.getLogger(__name__)

def create_sentiment_table(conn: PGConnection) -> None:
    """Creates the sentiment_logs table if it does not exist."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp BIGINT NOT NULL,
                    batch_size INT NOT NULL,
                    overall_sentiment_score FLOAT,
                    sentiment_label VARCHAR(50),
                    grok_model_used VARCHAR(50),
                    raw_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_sentiment_logs_timestamp ON sentiment_logs(timestamp);
            """)
        conn.commit()
        logger.debug("sentiment_logs table ensured.")
    except Exception as e:
        logger.error(f"Error creating sentiment_logs table: {e}")
        conn.rollback()

def insert_sentiment_log(
    conn: PGConnection,
    timestamp: int,
    batch_size: int,
    score: float,
    label: str,
    model_used: str,
    raw_response: str
) -> bool:
    """Inserts a sentiment log entry into the database."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sentiment_logs 
                (timestamp, batch_size, overall_sentiment_score, sentiment_label, grok_model_used, raw_response)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (timestamp, batch_size, score, label, model_used, raw_response))
        conn.commit()
        logger.debug(f"Inserted sentiment log for timestamp {timestamp}")
        return True
    except Exception as e:
        logger.error(f"Error inserting sentiment log: {e}")
        conn.rollback()
        return False
