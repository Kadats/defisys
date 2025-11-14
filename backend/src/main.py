# Importa a função principal do seu novo módulo system_runner
from system_runner import run_trading_system
from logging_config import setup_logging
from config import LOG_LEVEL

# Configure logging once, here in the entrypoint
logger = setup_logging(level=LOG_LEVEL)

if __name__ == "__main__":
    run_trading_system()

