"""
Database and Model Reset Utility.

This script completely clears all trading history, predictions, cached models,
AND market data (TVL, Volatility, Fees) to force a fresh simulation from scratch.

Usage:
    python -m backend.src.utils.reset_db
"""
import os
import logging
import psycopg2
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment or use default."""
    return os.environ.get(
        'DATABASE_URL',
        'postgresql://defisys_user:defisys_pass@db:5432/defisys_db'
    )

def reset_database():
    """
    Truncate ALL tables (Trading History + Market Data) to force a fresh start.
    """
    database_url = get_database_url()
    
    try:
        # Connect to PostgreSQL
        logger.info(f"Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Lista completa de tabelas para apagar (Resultados + Dados de Mercado)
        # A ordem não importa muito devido ao CASCADE, mas é bom listar tudo.
        tables_to_clear = [
            # 1. Resultados da Simulação (O que o bot fez)
            'trades', 
            'positions',
            'positions_log',       # Nome usado no log do seu sistema
            'signals',
            'ml_predictions',      # Nome correto visto nos logs
            'predictions',         # Mantendo por compatibilidade
            
            # 2. Dados de Mercado (O que o bot lê) - AQUI ESTAVA O PROBLEMA
            'uniswap_pool_data',             # O culpado do TVL=1
            'fear_and_greed_index',
            'binance_futures_funding_rate',
            'binance_futures_open_interest',
            'implied_volatility',
            'bitcoin_on_chain_metrics',
            
            # 3. Dados de Preço (Candles)
            # Adicione aqui se souber o nome exato (ex: 'btcusdt_4h'), 
            # senão o pipeline sobrescreve.
            'btcusdt_4h',
            'btcusdt_1d'
        ]
        
        logger.info("Starting TOTAL database cleanup (Terra Arrasada)...")
        
        for table in tables_to_clear:
            try:
                # Use TRUNCATE for fast deletion (resets auto-increment)
                # CASCADE garante que tabelas dependentes também sejam limpas
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
                logger.info(f"✓ Cleared table: {table}")
            except psycopg2.errors.UndefinedTable:
                # É normal falhar se a tabela ainda não existir (primeira rodada)
                conn.rollback() 
                logger.debug(f"Table '{table}' not found (skipping).")
            except Exception as e:
                logger.warning(f"⚠ Could not clear table '{table}': {e}")
                conn.rollback()
        
        # Commit the changes
        conn.commit()
        logger.info("Database truncation complete.")
        
        # Close connection
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        # Não damos raise aqui para permitir que a limpeza de arquivos continue
        
def delete_model_files():
    """
    Delete cached ML model files to force retraining.
    """
    # Get the project root (relative to this script location)
    # backend/src/utils -> backend/src -> backend -> root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent.parent
    
    # Possible model file locations
    model_paths = [
        project_root / 'backend' / 'data' / 'models' / 'model_v1.pkl',
        project_root / 'backend' / 'data' / 'model.pkl',
        project_root / 'data' / 'models' / 'model_v1.pkl',
    ]
    
    logger.info("Checking for cached model files...")
    
    deleted_count = 0
    for model_path in model_paths:
        if model_path.exists():
            try:
                model_path.unlink()
                logger.info(f"✓ Deleted model file: {model_path}")
                deleted_count += 1
            except Exception as e:
                logger.warning(f"⚠ Could not delete {model_path}: {e}")
        else:
            logger.debug(f"Model file not found: {model_path}")
    
    if deleted_count == 0:
        logger.info("No cached model files found.")
    else:
        logger.info(f"Deleted {deleted_count} model file(s).")

def main():
    """
    Main execution: Reset database and delete model files.
    """
    logger.info("=" * 60)
    logger.info("DEFISYS V15 - HARD RESET (FULL WIPE)")
    logger.info("=" * 60)
    
    # Step 1: Clear database tables
    logger.info("\n[Step 1/2] Clearing database tables...")
    reset_database()
    
    # Step 2: Delete model files
    logger.info("\n[Step 2/2] Deleting cached model files...")
    delete_model_files()
    
    # Done
    logger.info("\n" + "=" * 60)
    logger.info("✅ System Reset Complete.")
    logger.info("Ready for fresh V15 Simulation!")
    logger.info("Run 'python -m backend.src.data.pipeline' to repopulate correct data.")
    logger.info("=" * 60)

if __name__ == '__main__':
    main()