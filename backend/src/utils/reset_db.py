"""
Database and Model Reset Utility.

This script completely clears all trading history, predictions, and cached models
to force a fresh simulation from scratch.

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
        'postgresql://user:password@localhost:5432/defisys'
    )

def reset_database():
    """
    Truncate all trading-related tables to force a fresh start.
    """
    database_url = get_database_url()
    
    try:
        # Connect to PostgreSQL
        logger.info(f"Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # List of tables to clear
        tables_to_clear = [
            'predictions',
            'trades', 
            'positions',
            'signals'
        ]
        
        logger.info("Starting database cleanup...")
        
        for table in tables_to_clear:
            try:
                # Use TRUNCATE for fast deletion (resets auto-increment)
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
                logger.info(f"✓ Cleared table: {table}")
            except psycopg2.errors.UndefinedTable:
                logger.warning(f"⚠ Table '{table}' does not exist, skipping...")
                conn.rollback()  # Rollback the failed transaction
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
        raise

def delete_model_files():
    """
    Delete cached ML model files to force retraining.
    """
    # Get the project root (2 levels up from utils)
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
    logger.info("DEFISYS V15 - HARD RESET")
    logger.info("=" * 60)
    
    # Step 1: Clear database tables
    logger.info("\n[Step 1/2] Clearing database tables...")
    try:
        reset_database()
    except Exception as e:
        logger.error(f"Database reset failed. Continuing with model cleanup...")
    
    # Step 2: Delete model files
    logger.info("\n[Step 2/2] Deleting cached model files...")
    delete_model_files()
    
    # Done
    logger.info("\n" + "=" * 60)
    logger.info("✅ System Reset Complete.")
    logger.info("Ready for fresh V15 Simulation with AccumulatorStrategy!")
    logger.info("=" * 60)

if __name__ == '__main__':
    main()
