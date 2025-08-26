import os
try:
	from pydantic_settings import BaseSettings
	_HAS_PYDANTIC = True
except Exception:
	BaseSettings = object
	_HAS_PYDANTIC = False


class Settings(BaseSettings if _HAS_PYDANTIC else object):
	# Paths
	PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
	DATA_DIR: str = os.path.join(PROJECT_ROOT, 'backend', 'data')
	DB_FILE: str = os.path.join(DATA_DIR, 'crypto_data.db')

	# API endpoints (change via env if needed)
	BINANCE_API_BASE_URL: str = "https://api.binance.com/api/v3"
	BINANCE_FUTURES_API_BASE_URL: str = "https://fapi.binance.com"
	FNG_API_URL: str = "https://api.alternative.me/fng/"
	BLOCKCHAIR_API_URL: str = "https://api.blockchair.com/bitcoin/stats"

	# Defaults
	DEFAULT_SYMBOL: str = "BTCUSDT"
	DEFAULT_INTERVAL: str = "1d"
	DEFAULT_KLINES_LIMIT: int = 1000
	DEFAULT_HISTORICAL_DAYS: int = 365
	# Logging
	LOG_LEVEL: str = "INFO"

	if _HAS_PYDANTIC:
		class Config:
			env_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
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
			self.FNG_API_URL = os.environ.get('FNG_API_URL', "https://api.alternative.me/fng/")
			self.BLOCKCHAIR_API_URL = os.environ.get('BLOCKCHAIR_API_URL', "https://api.blockchair.com/bitcoin/stats")

			# Defaults
			self.DEFAULT_SYMBOL = os.environ.get('DEFAULT_SYMBOL', "BTCUSDT")
			self.DEFAULT_INTERVAL = os.environ.get('DEFAULT_INTERVAL', "1d")
			self.DEFAULT_KLINES_LIMIT = int(os.environ.get('DEFAULT_KLINES_LIMIT', 1000))
			self.DEFAULT_HISTORICAL_DAYS = int(os.environ.get('DEFAULT_HISTORICAL_DAYS', 365))


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
DEFAULT_SYMBOL = _settings.DEFAULT_SYMBOL
DEFAULT_INTERVAL = _settings.DEFAULT_INTERVAL
DEFAULT_KLINES_LIMIT = _settings.DEFAULT_KLINES_LIMIT
DEFAULT_HISTORICAL_DAYS = _settings.DEFAULT_HISTORICAL_DAYS
LOG_LEVEL = _settings.LOG_LEVEL

