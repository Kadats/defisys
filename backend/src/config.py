import os

# Caminhos do Projeto
# __file__ é o caminho do arquivo atual (config.py).
# os.path.dirname(__file__) te leva para 'backend/src/'
# os.path.abspath(...) transforma em caminho absoluto.
# Os.path.join navega até a raiz do projeto (defisys) para depois ir para backend/data
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'backend', 'data')
DB_FILE = os.path.join(DATA_DIR, 'crypto_data.db')

# Configurações da API da Binance
BINANCE_API_BASE_URL = "https://api.binance.com/api/v3"
BINANCE_FUTURES_API_BASE_URL = "https://fapi.binance.com"
# Configurações da API da Alternative.me
FNG_API_URL = "https://api.alternative.me/fng/"
# Configurações da API da Blockchair para dados On-Chain de Bitcoin
BLOCKCHAIR_API_URL = "https://api.blockchair.com/bitcoin/stats"

# Configurações de Coleta de Dados Padrão
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_INTERVAL = "1d"
DEFAULT_KLINES_LIMIT = 1000 # Máximo de velas por requisição
DEFAULT_HISTORICAL_DAYS = 365 # Coletar 1 ano de dados se DB vazio

