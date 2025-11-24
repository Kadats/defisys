import os
try:
	from pydantic_settings import BaseSettings
	from pydantic import ConfigDict # <-- MUDANÇA 1: Importar ConfigDict
	_HAS_PYDANTIC = True
except Exception:
	BaseSettings = object
	ConfigDict = None # <-- Adicionar fallback
	_HAS_PYDANTIC = False

class Settings(BaseSettings if _HAS_PYDANTIC else object):
	# Paths
	PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
	DATA_DIR: str = os.path.join(PROJECT_ROOT, 'backend', 'data')
	DB_FILE: str = os.path.join(DATA_DIR, 'crypto_data.db')

	# API endpoints (change via env if needed)
	BINANCE_API_BASE_URL: str = "https://api.binance.com/api/v3"
	BINANCE_FUTURES_API_BASE_URL: str = "https://fapi.binance.com"
	DERIBIT_API_BASE_URL: str = "https://www.deribit.com/api/v2"
	FNG_API_URL: str = "https://api.alternative.me/fng/"
	BLOCKCHAIR_API_URL: str = "https://api.blockchair.com/bitcoin/stats"

	# Defaults
	DEFAULT_SYMBOL: str = "BTCUSDT"
	DEFAULT_INTERVAL: str = "4h"
	DEFAULT_KLINES_LIMIT: int = 1000
	# Collect 5 years of 4h klines for SMA_200 indicator (1825 days = ~5 years)
	DEFAULT_HISTORICAL_DAYS: int = 1825

	# The Graph - Uniswap v3 configuration (configurable)
	# Base gateway URL (no API key or subgraph id included)
	THEGRAPH_UNISWAP_V3_URL: str = "https://gateway.thegraph.com/api/"

	# Mapping of network name -> Uniswap v3 subgraph ID
	THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS: dict = {
		"mainnet": "ELUcwgpm14LKPLrdduc6pTfS_LpC7xdM14iBC_19I70",
		"polygon": "3hCPRGf4z88VC5rsBKU5AA9FBBq5nF3jbKJG7VZCbhjm",
	}

	# Default network to query (can be 'mainnet' or 'polygon')
	DEFAULT_NETWORK: str = "polygon"

	# Default Uniswap pool id for Polygon (used by the Uniswap collector)
	DEFAULT_POLYGON_POOL_ID: str = "0x847b64f9d3a95e977d157866447a5c0a5dfa0ee5"

	# The Graph API key (set in .env)
	THEGRAPH_API_KEY: str = ""
	# Logging
	LOG_LEVEL: str = "INFO"

	# Smart Harvest - Gas fees simulation (Polygon/Ethereum)
	SIMULATED_GAS_FEE_USD: float = 0.50

	# Walk-Forward Validation: Train on past, test on recent
	# Model trains only on data before this date, backtests from this date onward
	TRAIN_TEST_SPLIT_DATE: str = "2022-01-01"

	if _HAS_PYDANTIC:
		model_config = ConfigDict(
			env_file=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
		)
	else:
		# Fallback: read environment variables directly when pydantic-settings is not available
		def __init__(self):
			# Paths
			self.PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
			self.DATA_DIR = os.path.join(self.PROJECT_ROOT, 'backend', 'data')
			self.DB_FILE = os.path.join(self.DATA_DIR, 'crypto_data.db')

			# API endpoints (change via env if needed)
			self.BINANCE_API_BASE_URL = os.environ.get('BINANCE_API_BASE_URL', "https://api.binance.com/api/v3")
			self.BINANCE_FUTURES_API_BASE_URL = os.environ.get('BINANCE_FUTURES_API_BASE_URL', "https://fapi.binance.com")
			self.DERIBIT_API_BASE_URL = os.environ.get('DERIBIT_API_BASE_URL', "https://www.deribit.com/api/v2")
			self.FNG_API_URL = os.environ.get('FNG_API_URL', "https://api.alternative.me/fng/")
			self.BLOCKCHAIR_API_URL = os.environ.get('BLOCKCHAIR_API_URL', "https://api.blockchair.com/bitcoin/stats")

			# Defaults
			self.DEFAULT_SYMBOL = os.environ.get('DEFAULT_SYMBOL', "BTCUSDT")
			self.DEFAULT_INTERVAL = os.environ.get('DEFAULT_INTERVAL', "4h")
			self.DEFAULT_KLINES_LIMIT = int(os.environ.get('DEFAULT_KLINES_LIMIT', 1000))
			self.DEFAULT_HISTORICAL_DAYS = int(os.environ.get('DEFAULT_HISTORICAL_DAYS', 1825))
			self.SIMULATED_GAS_FEE_USD = float(os.environ.get('SIMULATED_GAS_FEE_USD', 0.50))


# Instantiate settings for module-level import
_settings = Settings()

# Export commonly used constants for backward compatibility
PROJECT_ROOT = _settings.PROJECT_ROOT
DATA_DIR = _settings.DATA_DIR
DB_FILE = _settings.DB_FILE
BINANCE_API_BASE_URL = _settings.BINANCE_API_BASE_URL
BINANCE_FUTURES_API_BASE_URL = _settings.BINANCE_FUTURES_API_BASE_URL
FNG_API_URL = _settings.FNG_API_URL
BLOCKCHAIR_API_URL = _settings.BLOCKCHAIR_API_URL
THEGRAPH_UNISWAP_V3_URL = _settings.THEGRAPH_UNISWAP_V3_URL
THEGRAPH_API_KEY = _settings.THEGRAPH_API_KEY
DEFAULT_SYMBOL = _settings.DEFAULT_SYMBOL
DEFAULT_INTERVAL = _settings.DEFAULT_INTERVAL
DEFAULT_KLINES_LIMIT = _settings.DEFAULT_KLINES_LIMIT

DEFAULT_HISTORICAL_DAYS = _settings.DEFAULT_HISTORICAL_DAYS
LOG_LEVEL = _settings.LOG_LEVEL
SIMULATED_GAS_FEE_USD = _settings.SIMULATED_GAS_FEE_USD

# Walk-Forward Validation split date
TRAIN_TEST_SPLIT_DATE = _settings.TRAIN_TEST_SPLIT_DATE

# New exports for The Graph multi-subgraph support
THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS = _settings.THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS
DEFAULT_NETWORK = _settings.DEFAULT_NETWORK
DEFAULT_POLYGON_POOL_ID = _settings.DEFAULT_POLYGON_POOL_ID
DERIBIT_API_BASE_URL = _settings.DERIBIT_API_BASE_URL

