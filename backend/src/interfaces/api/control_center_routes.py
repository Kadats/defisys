"""Control Center API routes."""

from types import ModuleType
from typing import Any

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool


def create_control_center_router(
    api_deps: ModuleType,
    sandbox_request_model: type[Any],
) -> APIRouter:
    """Create Control Center router using API module dependencies."""
    router = APIRouter(tags=["Control Center"])

    @router.get("/api/system/health")
    async def get_system_health() -> dict[str, Any]:
        """Retorna o estado de saúde dos RPCs."""
        return api_deps.rpc_manager.get_all_health()

    @router.get("/api/system/logs")
    def get_system_logs() -> list[str]:
        """Retorna as últimas 50 linhas do log persistente."""
        log_file = api_deps.os.path.join(
            api_deps.PROJECT_ROOT,
            "backend",
            "logs",
            "defisys.log",
        )

        if not api_deps.os.path.exists(log_file):
            return []

        try:
            with open(log_file, "r", encoding="utf-8") as file_handle:
                lines = file_handle.readlines()
                return [line.strip() for line in lines[-50:]]
        except Exception as exc:
            api_deps.logger.error("Erro ao ler arquivo de log: %s", exc)
            return [f"Erro ao recuperar logs: {exc}"]

    @router.get("/api/system/indicators")
    def get_indicators() -> dict[str, Any]:
        """Retorna indicadores críticos em tempo real."""
        klines_table_name = f"{api_deps.DEFAULT_SYMBOL}_{api_deps.DEFAULT_INTERVAL}_klines".lower()
        df = api_deps.get_data_from_db(klines_table_name, limit=100)
        if df.empty:
            return {"rsi": 0, "fear_and_greed": 0, "market_regime": "unknown"}
        return api_deps.heuristics.get_market_indicators(df)

    @router.post("/api/sandbox/run")
    async def post_sandbox_run(payload: sandbox_request_model) -> dict[str, Any]:
        """Dispara uma simulação no Sandbox Lab."""
        return await run_in_threadpool(api_deps.run_sandbox_simulation, payload)

    return router
