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
	
	# Database Configuration (PostgreSQL)
	# Default to docker compose service name 'postgres' or 'localhost' for local dev
	DATABASE_URL: str = os.environ.get(
		'DATABASE_URL', 
		'postgresql://user:password@localhost:5432/defisys'
	)

	# API endpoints (change via env if needed)
	BINANCE_API_KEY: str = os.environ.get("BINANCE_API_KEY", "")
	BINANCE_API_SECRET: str = os.environ.get("BINANCE_API_SECRET", "")
	BINANCE_API_BASE_URL: str = "https://api.binance.com/api/v3"
	BINANCE_FUTURES_API_BASE_URL: str = "https://fapi.binance.com"
	DERIBIT_API_BASE_URL: str = "https://www.deribit.com/api/v2"
	FNG_API_URL: str = "https://api.alternative.me/fng/"
	BLOCKCHAIR_API_URL: str = "https://api.blockchair.com/bitcoin/stats"

	# Defaults
	DEFAULT_SYMBOL: str = "BTCUSDT"
	DEFAULT_INTERVAL: str = "4h"
	DEFAULT_KLINES_LIMIT: int = 1000
	# Collect full BTC cycle history from BTCUSDT launch (2017-08-17) to present
	# Covers all major bull/bear cycles: 2017 bull, 2018 bear, 2020-2021 super bull, 2022 bear, 2024 bull
	# ~8.5 years of 4h klines = ~3200 days
	DEFAULT_HISTORICAL_DAYS: int = 3200

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
	SIMULATED_GAS_FEE_USD: float = 0.10
	SLIPPAGE_PCT: float = 0.001

	# Gas Reserve: Always keep this amount in USD for operational costs (harvests, rebalancing)
	GAS_RESERVE_USD: float = 50.0

	# Dynamic Allocation: Position sizing parameters
	# Minimum liquid cash buffer (% of balance) to keep for interest + gas fees
	MIN_LIQUID_BUFFER: float = 0.20  # Always keep at least 20% liquid
	# Maximum allocation percentage when market conditions are good
	MAX_ALLOCATION_PCT: float = 0.80  # Never allocate more than 80% of balance
	# Base allocation when no special conditions
	BASE_ALLOCATION_PCT: float = 0.20  # Start with 20% of balance
	# Drawdown threshold to increase allocation aggressively
	DRAWDOWN_THRESHOLD: float = 0.30  # If price is 30% below ATH, become more aggressive
	# Fear & Greed threshold to increase allocation
	FNG_THRESHOLD_AGGRESSIVE: float = 20.0  # If FNG < 20 (Extreme Fear), increase allocation

	# Refinancing threshold for margin reuse decisions
	HF_REFINANCE_THRESHOLD: float = 2.0

	# Safe HF target immediately after borrowing (guardrail against churn)
	# If HF would drop below this after a borrow, reduce or skip the borrow
	SAFE_HF_AFTER_BORROW: float = 1.6

	# Walk-Forward Validation: Train on past, test on recent
	# Model trains only on data before this date, backtests from this date onward
	# 2 years ago from Nov 2025 ≈ June 2023: tests on 2023-2025 recovery period
	TRAIN_TEST_SPLIT_DATE: str = "2023-06-01"

	# Machine Learning Configuration
	# Hard cut for Walk-Forward validation - train before, test after
	# Train on: 2017-08-17 to 2023-12-31 (full historical cycles)
	# Backtest on: 2024-01-01 to 2026-02-20 (Halving cycle + post-ETF market)
	ML_TRAIN_SPLIT_DATE: str = "2025-06-01"
	# Minimum probability threshold to trigger a buy signal (65%)
	ML_CONFIDENCE_THRESHOLD: float = 0.65
	# Price must rise by at least 4% to be considered a positive target (swing trade)
	ML_TARGET_MIN_CHANGE: float = 0.04
	# Number of candles ahead to look for the target move (30 candles = 5 days for 4h candles)
	ML_PREDICTION_HORIZON: int = 30

	# Gemini API Testing: Limit backtest window to avoid rate limit during development
	# Set GEMINI_BACKTEST_DAYS=30 in .env to use only last N days for backtest
	# Useful for testing Gemini API integration without hitting free tier rate limits
	GEMINI_BACKTEST_DAYS: int = int(os.environ.get("GEMINI_BACKTEST_DAYS", 0))  # 0 = use full window

	# Grok (xAI) API Settings
	GROK_API_KEY: str = os.environ.get("GROK_API_KEY", "")
	GROK_MODEL: str = os.environ.get("GROK_MODEL", "grok-beta")
	GROK_API_BASE_URL: str = os.environ.get("GROK_API_BASE_URL", "https://api.x.ai/v1/")
	GROK_API_DELAY_SECONDS: float = float(os.environ.get("GROK_API_DELAY_SECONDS", 2.0))

	# Multi-pool and entry sizing
	# Maximum number of concurrently active LPs
	MAX_ACTIVE_LPS: int = 4
	# Fraction of available safe balance to allocate per entry (25% = 0.25)
	ENTRY_SIZE_PCT: float = 0.25

	# V3 Dynamic ATR Ranges
	# ATR multipliers for determining LP range width based on volatility
	# Since 4h ATR is small, we use large multipliers to cover days/weeks of movement
	ATR_MULTIPLIER_BULLISH_LOWER: float = 10.0  # Downside protection
	ATR_MULTIPLIER_BULLISH_UPPER: float = 25.0  # Allow more room to run up
	ATR_MULTIPLIER_NEUTRAL: float = 20.0  # Symmetric wide range for stability

	# V13 Smart Reserve - Emergency Fund and Leverage Constraints
	# Minimum USD Cash Reserve as % of Total Equity (Emergency Fund)
	MIN_RESERVE_PCT: float = 0.20  # Keep 20% of Total Equity as USD Cash
	# V14 Flywheel - Dynamic reserve target as % of total equity
	TARGET_RESERVE_RATIO: float = 0.20  # Target 20% of equity held in USD
	# V14 Flywheel - Lazy harvest trigger to save gas
	MIN_HARVEST_USD: float = 15.0
	# V14 Flywheel - Max debt allowed relative to collateral (conservative LTV)
	MAX_DEBT_RATIO: float = 0.45
	# Maximum Debt-to-Reserve Ratio: Never borrow more than N times the cash reserve
	MAX_DEBT_TO_RESERVE_RATIO: float = 3.0  # Constraint: debt <= 3x cash reserve
	# Deleveraging Threshold: Use cash reserve to pay debt if HF drops below this
	DELEVERAGE_THRESHOLD_HF: float = 1.6  # Trigger deleveraging at HF < 1.6

	# Kill Switch Limits
	MAX_DAILY_DRAWDOWN: float = 0.10  # 10% daily drawdown limit
	MAX_GLOBAL_DRAWDOWN: float = 0.15  # 15% global drawdown limit

	# Level 2 Resilience & Infrastructure
	ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "sandbox")
	RPC_URL_PRIMARY: str = os.environ.get("RPC_URL_PRIMARY", "")
	RPC_URL_SECONDARY: str = os.environ.get("RPC_URL_SECONDARY", "")
	RPC_URL_DECENTRALIZED: str = os.environ.get("RPC_URL_DECENTRALIZED", "")
	NETWORK_TIMEOUT_SECONDS: float = 5.0
	NETWORK_RETRY_ATTEMPTS: int = 3

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
			
			# Database Configuration (PostgreSQL)
			self.DATABASE_URL = os.environ.get(
				'DATABASE_URL',
				'postgresql://user:password@localhost:5432/defisys'
			)

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
			self.DEFAULT_HISTORICAL_DAYS = int(os.environ.get('DEFAULT_HISTORICAL_DAYS', 3200))
			self.SIMULATED_GAS_FEE_USD = float(os.environ.get('SIMULATED_GAS_FEE_USD', 0.10))
			self.SLIPPAGE_PCT = float(os.environ.get('SLIPPAGE_PCT', 0.001))
			self.TARGET_RESERVE_RATIO = float(os.environ.get('TARGET_RESERVE_RATIO', 0.20))
			self.MIN_HARVEST_USD = float(os.environ.get('MIN_HARVEST_USD', 15.0))
			self.MAX_DEBT_RATIO = float(os.environ.get('MAX_DEBT_RATIO', 0.45))
			self.MAX_DAILY_DRAWDOWN = float(os.environ.get('MAX_DAILY_DRAWDOWN', 0.10))
			self.MAX_GLOBAL_DRAWDOWN = float(os.environ.get('MAX_GLOBAL_DRAWDOWN', 0.15))
			
			# Level 2 Resilience & Infrastructure
			self.ENVIRONMENT = os.environ.get("ENVIRONMENT", "sandbox")
			self.PRIVATE_RPC_URL = os.environ.get("PRIVATE_RPC_URL", "")
			self.NETWORK_TIMEOUT_SECONDS = float(os.environ.get("NETWORK_TIMEOUT_SECONDS", 5.0))
			self.NETWORK_RETRY_ATTEMPTS = int(os.environ.get("NETWORK_RETRY_ATTEMPTS", 3))

			# Machine Learning Configuration
			self.ML_TRAIN_SPLIT_DATE = os.environ.get('ML_TRAIN_SPLIT_DATE', '2026-01-01')
			self.ML_CONFIDENCE_THRESHOLD = float(os.environ.get('ML_CONFIDENCE_THRESHOLD', 0.65))
			self.ML_TARGET_MIN_CHANGE = float(os.environ.get('ML_TARGET_MIN_CHANGE', 0.02))
			self.ML_PREDICTION_HORIZON = int(os.environ.get('ML_PREDICTION_HORIZON', 12))
			self.GEMINI_BACKTEST_DAYS = int(os.environ.get('GEMINI_BACKTEST_DAYS', 0))

			# Grok (xAI) API Settings
			self.GROK_API_KEY = os.environ.get("GROK_API_KEY", "")
			self.GROK_MODEL = os.environ.get("GROK_MODEL", "grok-beta")
			self.GROK_API_BASE_URL = os.environ.get("GROK_API_BASE_URL", "https://api.x.ai/v1/")
			self.GROK_API_DELAY_SECONDS = float(os.environ.get("GROK_API_DELAY_SECONDS", 2.0))

# Instantiate settings for module-level import
_settings = Settings()

# Export commonly used constants for backward compatibility
PROJECT_ROOT = _settings.PROJECT_ROOT
DATA_DIR = _settings.DATA_DIR
DATABASE_URL = _settings.DATABASE_URL
BINANCE_API_KEY = _settings.BINANCE_API_KEY
BINANCE_API_SECRET = _settings.BINANCE_API_SECRET
BINANCE_API_BASE_URL = _settings.BINANCE_API_BASE_URL
BINANCE_FUTURES_API_BASE_URL = _settings.BINANCE_FUTURES_API_BASE_URL
FNG_API_URL = _settings.FNG_API_URL
BLOCKCHAIR_API_URL = _settings.BLOCKCHAIR_API_URL
THEGRAPH_UNISWAP_V3_URL = _settings.THEGRAPH_UNISWAP_V3_URL
THEGRAPH_API_KEY = _settings.THEGRAPH_API_KEY

def validate_production_secrets():
    """Valida se as chaves necessárias estão presentes em modo produção."""
    if _settings.ENVIRONMENT == "production":
        missing = []
        if not _settings.BINANCE_API_KEY: missing.append("BINANCE_API_KEY")
        if not _settings.BINANCE_API_SECRET: missing.append("BINANCE_API_SECRET")
        
        # Auditoria Nível 3.2: Verificar existência de .env em produção
        env_path = os.path.abspath(os.path.join(_settings.PROJECT_ROOT, ".env"))
        if not os.path.exists(env_path):
            import logging
            logging.getLogger(__name__).warning(f"⚠️ Arquivo .env não encontrado em {env_path}. Usando variáveis de ambiente do sistema.")
            
        if missing:
            raise RuntimeError(f"⚠️ MODO PRODUÇÃO ATIVO: Faltam chaves de segredo: {', '.join(missing)}")
        # Nunca logar o valor das chaves
        import logging
        logging.getLogger(__name__).info("✓ Chaves de produção validadas com sucesso.")
DEFAULT_SYMBOL = _settings.DEFAULT_SYMBOL
DEFAULT_INTERVAL = _settings.DEFAULT_INTERVAL
DEFAULT_KLINES_LIMIT = _settings.DEFAULT_KLINES_LIMIT

DEFAULT_HISTORICAL_DAYS = _settings.DEFAULT_HISTORICAL_DAYS
LOG_LEVEL = _settings.LOG_LEVEL
SIMULATED_GAS_FEE_USD = _settings.SIMULATED_GAS_FEE_USD
SLIPPAGE_PCT = _settings.SLIPPAGE_PCT
GAS_RESERVE_USD = _settings.GAS_RESERVE_USD

# Dynamic Allocation parameters
MIN_LIQUID_BUFFER = _settings.MIN_LIQUID_BUFFER
MAX_ALLOCATION_PCT = _settings.MAX_ALLOCATION_PCT
BASE_ALLOCATION_PCT = _settings.BASE_ALLOCATION_PCT
DRAWDOWN_THRESHOLD = _settings.DRAWDOWN_THRESHOLD
FNG_THRESHOLD_AGGRESSIVE = _settings.FNG_THRESHOLD_AGGRESSIVE
HF_REFINANCE_THRESHOLD = _settings.HF_REFINANCE_THRESHOLD
SAFE_HF_AFTER_BORROW = _settings.SAFE_HF_AFTER_BORROW

# Walk-Forward Validation split date
TRAIN_TEST_SPLIT_DATE = _settings.TRAIN_TEST_SPLIT_DATE

# Machine Learning Configuration
ML_TRAIN_SPLIT_DATE = _settings.ML_TRAIN_SPLIT_DATE
ML_CONFIDENCE_THRESHOLD = _settings.ML_CONFIDENCE_THRESHOLD
ML_TARGET_MIN_CHANGE = _settings.ML_TARGET_MIN_CHANGE
ML_PREDICTION_HORIZON = _settings.ML_PREDICTION_HORIZON
GEMINI_BACKTEST_DAYS = _settings.GEMINI_BACKTEST_DAYS

# Grok (xAI) API exports
GROK_API_KEY = _settings.GROK_API_KEY
GROK_MODEL = _settings.GROK_MODEL
GROK_API_BASE_URL = _settings.GROK_API_BASE_URL
GROK_API_DELAY_SECONDS = _settings.GROK_API_DELAY_SECONDS

# New exports for The Graph multi-subgraph support
THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS = _settings.THEGRAPH_UNISWAP_V3_SUBGRAPH_IDS
DEFAULT_NETWORK = _settings.DEFAULT_NETWORK
DEFAULT_POLYGON_POOL_ID = _settings.DEFAULT_POLYGON_POOL_ID
DERIBIT_API_BASE_URL = _settings.DERIBIT_API_BASE_URL

# Multi-pool and entry sizing (exports)
MAX_ACTIVE_LPS = _settings.MAX_ACTIVE_LPS
ENTRY_SIZE_PCT = _settings.ENTRY_SIZE_PCT

# V3 Dynamic ATR Ranges (exports)
ATR_MULTIPLIER_BULLISH_LOWER = _settings.ATR_MULTIPLIER_BULLISH_LOWER
ATR_MULTIPLIER_BULLISH_UPPER = _settings.ATR_MULTIPLIER_BULLISH_UPPER
ATR_MULTIPLIER_NEUTRAL = _settings.ATR_MULTIPLIER_NEUTRAL

# V13 Smart Reserve (exports)
MIN_RESERVE_PCT = _settings.MIN_RESERVE_PCT
TARGET_RESERVE_RATIO = _settings.TARGET_RESERVE_RATIO
MIN_HARVEST_USD = _settings.MIN_HARVEST_USD
MAX_DEBT_RATIO = _settings.MAX_DEBT_RATIO
MAX_DEBT_TO_RESERVE_RATIO = _settings.MAX_DEBT_TO_RESERVE_RATIO
DELEVERAGE_THRESHOLD_HF = _settings.DELEVERAGE_THRESHOLD_HF
MAX_DAILY_DRAWDOWN = _settings.MAX_DAILY_DRAWDOWN
MAX_GLOBAL_DRAWDOWN = _settings.MAX_GLOBAL_DRAWDOWN

# Level 2 Resilience & Infrastructure (exports)
ENVIRONMENT = _settings.ENVIRONMENT
RPC_URL_PRIMARY = _settings.RPC_URL_PRIMARY
RPC_URL_SECONDARY = _settings.RPC_URL_SECONDARY
RPC_URL_DECENTRALIZED = _settings.RPC_URL_DECENTRALIZED
NETWORK_TIMEOUT_SECONDS = _settings.NETWORK_TIMEOUT_SECONDS
NETWORK_RETRY_ATTEMPTS = _settings.NETWORK_RETRY_ATTEMPTS
