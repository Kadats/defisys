import logging
import psycopg2
from psycopg2 import extras
from psycopg2.extensions import connection as PGConnection
import pandas as pd

from .connection import create_connection

logger = logging.getLogger(__name__)

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


def clear_predictions_data():
    """Limpa apenas a tabela de predições de ML."""
    conn = create_connection()
    if not conn:
        logger.error("Não foi possível conectar ao banco para limpar predições")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM ml_predictions")
        conn.commit()
        logger.info("🧹 Predições de ML anteriores limpas com sucesso.")
    except Exception as exc:
        logger.error(f"Erro ao limpar predições: {exc}")
        conn.rollback()
    finally:
        conn.close()
