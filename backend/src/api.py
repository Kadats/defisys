import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import sys
import pandas as pd

# Imports internos
from backend.src.ai import heuristics
from backend.src.core.rpc_manager import RPCManager
from backend.src.data.pipeline import sync_market_data
from backend.src.interfaces.api import (
    create_control_center_router,
    create_dashboard_router,
    dependencies as api_dependencies,
    create_simulation_read_router,
    create_simulation_execution_router,
    paper_runtime_router,
    SandboxRunRequest,
    websocket_router,
)
from backend.src.utils.analytics import calculate_yearly_metrics
from backend.src.utils.log_handler import WebSocketHandler
from .config import (
    DEFAULT_SYMBOL, DEFAULT_INTERVAL, DEFAULT_KLINES_LIMIT, LOG_LEVEL,
    RPC_URL_PRIMARY, RPC_URL_SECONDARY, RPC_URL_DECENTRALIZED, NETWORK_TIMEOUT_SECONDS,
    PROJECT_ROOT
)
from .logging_config import setup_logging

# Initialize logging BEFORE creating the FastAPI app
setup_logging(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

def _setup_websocket_logging() -> None:
    root_logger = logging.getLogger()
    if any(isinstance(handler, WebSocketHandler) for handler in root_logger.handlers):
        return

    handler = WebSocketHandler()
    handler.setLevel(root_logger.level or logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    root_logger.addHandler(handler)


def _startup_sync_enabled() -> bool:
    return os.getenv("SYNC_MARKET_DATA_ON_STARTUP", "false").lower() in {
        "1",
        "true",
        "yes",
    }


@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    _setup_websocket_logging()

    if _startup_sync_enabled():
        logger.info("🔄 Startup sync habilitado. Disparando sincronização em background.")

        async def _sync_job() -> None:
            try:
                await run_in_threadpool(sync_market_data)
                logger.info("✅ Sincronização de dados concluída em background.")
            except Exception as exc:
                logger.error(
                    "Erro durante sincronização de dados no startup: %s",
                    exc,
                    exc_info=True,
                )
                logger.warning(
                    "Servidor iniciado, mas sincronização de dados falhou. Execute manualmente se necessário."
                )

        asyncio.create_task(_sync_job())
    else:
        logger.info("⏭️ Startup sync desabilitado (SYNC_MARKET_DATA_ON_STARTUP=false).")

    yield


app = FastAPI(title="DefiSys API", lifespan=app_lifespan)
app.include_router(websocket_router)
app.include_router(paper_runtime_router)

# RPC Manager Singleton para a API (Auditoria 2.1 e 3.2)
rpc_manager = RPCManager(
    primary_url=RPC_URL_PRIMARY,
    secondary_url=RPC_URL_SECONDARY,
    decentralized_url=RPC_URL_DECENTRALIZED,
    timeout=NETWORK_TIMEOUT_SECONDS
)

# Permite configuração dinâmica via variável de ambiente (IP público)
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8501"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Cache simples em memória para não rodar backtest a cada F5
_SUMMARY_CACHE = {}
_SIMULATION_RUNNING = False  # Flag para rastrear se simulação está em andamento

# Backward-compatible module-level functions kept patchable by current tests.
def get_data_from_db(table_name: str, limit: int | None = None) -> pd.DataFrame:
    return api_dependencies.get_data_from_db(table_name, limit=limit)


def get_latest_simulation_summary():
    return api_dependencies.get_latest_simulation_summary()


def get_positions_from_db(include_open: bool = True, include_closed: bool = True) -> pd.DataFrame:
    return api_dependencies.get_positions_from_db(
        include_open=include_open,
        include_closed=include_closed,
    )


def get_predictions_from_db() -> pd.DataFrame:
    return api_dependencies.get_predictions_from_db()


app.include_router(
    create_control_center_router(
        sys.modules[__name__],
        SandboxRunRequest,
    )
)
app.include_router(
    create_simulation_execution_router(
        sys.modules[__name__],
    )
)
app.include_router(
    create_simulation_read_router(
        sys.modules[__name__],
    )
)
app.include_router(
    create_dashboard_router(
        sys.modules[__name__],
    )
)


def train_model_pipeline():
    """Backward-compatible API-level alias for model training use case."""
    return api_dependencies.train_model_pipeline()


def run_simulation(
    start_date: str = None,
    end_date: str = None,
    initial_capital: float = None,
    backtest_days: int | None = None,
    strategy_type: str = "accumulator",
    use_llm: bool = False,
):
    """Backward-compatible API-level alias for simulation use case."""
    return api_dependencies.run_simulation(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        backtest_days=backtest_days,
        strategy_type=strategy_type,
        use_llm=use_llm,
    )


def run_trading_system():
    """Backward-compatible API-level alias for full system use case."""
    return api_dependencies.run_trading_system()


def run_sandbox_simulation(payload: SandboxRunRequest):
    return api_dependencies.run_sandbox_simulation(payload)

def sanitize_for_json(obj):
    return api_dependencies.sanitize_for_json(obj)

def sanitize_df_for_json(df: pd.DataFrame) -> list:
    return api_dependencies.sanitize_df_for_json(df)
