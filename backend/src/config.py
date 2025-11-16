import os

try:
    from pydantic_settings import BaseSettings
    from pydantic import ConfigDict
    _HAS_PYDANTIC = True
except Exception:
    BaseSettings = object
    ConfigDict = None
    _HAS_PYDANTIC = False


class Settings(BaseSettings if _HAS_PYDANTIC else object):
    # Paths
    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    DATA_DIR: str = os.path.join(PROJECT_ROOT, 'data')
    DB_FILE: str = os.path.join(DATA_DIR, 'crypto_data.db')

    # API endpoints
    BINANCE_API_BASE_URL: str = "https://api.binance.com/api/v3"
    BINANCE_FUTURES_API_BASE_URL: str = "https://fapi.binance.com"
    DERIBIT_API_BASE_URL: str = "https://www.deribit.com/api/v2"
    FNG_API_URL: str = "https://api.alternative.me/fng/"
    BLOCKCHAIR_API_URL: str = "https://api.blockchair.com/bitcoin/stats"

    # Defaults
    DEFAULT_SYMBOL: str = "BTCUSDT"
    DEFAULT_INTERVAL: str = "1d"
    DEFAULT_KLINES_LIMIT: int = 1000
    DEFAULT_HISTORICAL_DAYS: int = 365

    # The Graph
    THEGRAPH_UNISWAP_V3_URL: str = "https://gateway.thegraph.com/api/"
    THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS: dict = {
        "mainnet": "ELUcwgpm14LKPLrdduc6pTfS_LpC7xdM14iBC_19I70",
        "polygon": "3hCPRGf4z88VC5rsBKU5AA9FBBq5nF3jbKJG7VZCbhjm",
    }

    DEFAULT_NETWORK: str = "polygon"
    DEFAULT_POLYGON_POOL_ID: str = "0x847b64f9d3a95e977d157866447a5c0a5dfa0ee5"

    THEGRAPH_API_KEY: str = ""
    LOG_LEVEL: str = "INFO"

    if _HAS_PYDANTIC:
        model_config = ConfigDict(
            env_file=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
        )
    else:
        def __init__(self):
            self.PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            self.DATA_DIR = os.path.join(self.PROJECT_ROOT, 'data')
            self.DB_FILE = os.path.join(self.DATA_DIR, 'crypto_data.db')

            self.BINANCE_API_BASE_URL = os.environ.get('BINANCE_API_BASE_URL', "https://api.binance.com/api/v3")
            self.BINANCE_FUTURES_API_BASE_URL = os.environ.get('BINANCE_FUTURES_API_BASE_URL', "https://fapi.binance.com")
            self.DERIBIT_API_BASE_URL = os.environ.get('DERIBIT_API_BASE_URL', "https://www.deribit.com/api/v2")
            self.FNG_API_URL = os.environ.get('FNG_API_URL', "https://api.alternative.me/fng/")
            self.BLOCKCHAIR_API_URL = os.environ.get('BLOCKCHAIR_API_URL', "https://api.blockchair.com/bitcoin/stats")

            self.DEFAULT_SYMBOL = os.environ.get('DEFAULT_SYMBOL', "BTCUSDT")
            self.DEFAULT_INTERVAL = os.environ.get('DEFAULT_INTERVAL', "1d")
            self.DEFAULT_KLINES_LIMIT = int(os.environ.get('DEFAULT_KLINES_LIMIT', 1000))
            self.DEFAULT_HISTORICAL_DAYS = int(os.environ.get('DEFAULT_HISTORICAL_DAYS', 365))


_settings = Settings()

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
THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS = _settings.THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS
DEFAULT_NETWORK = _settings.DEFAULT_NETWORK
DEFAULT_POLYGON_POOL_ID = _settings.DEFAULT_POLYGON_POOL_ID
DERIBIT_API_BASE_URL = _settings.DERIBIT_API_BASE_URL
