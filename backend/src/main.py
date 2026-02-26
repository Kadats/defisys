"""Main entry point - now primarily used for FastAPI server startup.

The trading system simulation is now triggered manually via API endpoints,
not automatically on startup. Market data synchronization happens automatically
on FastAPI startup via the @app.on_event("startup") handler in api.py.
"""
from .system_runner import run_trading_system
from .logging_config import setup_logging
from .config import LOG_LEVEL

# Configure logging once, here in the entrypoint
logger = setup_logging(level=LOG_LEVEL)

if __name__ == "__main__":
    # This block is kept for manual CLI execution if needed
    # Normal server startup goes through api.py via uvicorn
    logger.info("Manual execution mode - running full simulation...")
    run_trading_system()

