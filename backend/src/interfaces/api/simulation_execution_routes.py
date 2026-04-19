"""Model training and simulation execution routes."""

from __future__ import annotations

import asyncio
from types import ModuleType
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool


def create_simulation_execution_router(
    api_deps: ModuleType,
) -> APIRouter:
    """Create router for model train and simulation-run endpoints."""
    router = APIRouter(tags=["Simulation"])

    @router.post(
        "/api/model/train",
        tags=["Model"],
        summary="Train ML Model",
        description="Trains the XGBoost prediction model using historical data. Must be run before simulation.",
    )
    async def train_model():
        api_deps.logger.info("🤖 Endpoint /api/model/train chamado - iniciando treino do modelo...")

        def train_and_return():
            try:
                result = api_deps.train_model_pipeline()
                api_deps.logger.info("✓ Treinamento de ML concluído!")
                return result
            except Exception as exc:
                api_deps.logger.exception("❌ Erro no treinamento: %s", exc)
                return {
                    "success": False,
                    "error": str(exc),
                    "predictions_generated": 0,
                }

        result = await run_in_threadpool(train_and_return)

        if result.get("success"):
            return {
                "status": "completed",
                "message": f"Modelo treinado com sucesso! {result['predictions_generated']} predições geradas.",
                "data": result,
            }

        raise HTTPException(
            status_code=500,
            detail=f"Falha no treinamento do modelo: {result.get('error', 'Unknown error')}",
        )

    @router.post(
        "/api/simulation/run",
        summary="Run Simulation",
        description="Triggers the trading system to run without blocking the API.",
    )
    async def run_simulation_endpoint(payload: dict[str, Any]):
        api_deps.logger.info("🔍 Validando existência de predições no banco de dados...")
        predictions_df = api_deps.get_predictions_from_db()

        if predictions_df is None or predictions_df.empty:
            api_deps.logger.error("❌ Nenhuma predição encontrada no banco de dados!")
            raise HTTPException(
                status_code=400,
                detail="Modelo não treinado. Por favor, execute o treinamento antes de simular.",
            )

        api_deps.logger.info("✓ Validação OK: %s predições encontradas no banco", f"{len(predictions_df):,}")

        api_deps._SUMMARY_CACHE = {}
        api_deps._SIMULATION_RUNNING = True
        api_deps.logger.info("✓ Cache limpo e flag iniciado. Disparando simulação...")

        def run_and_mark_done():
            try:
                api_deps.run_simulation(
                    payload.get("start_date"),
                    payload.get("end_date"),
                    payload.get("initial_capital"),
                    backtest_days=payload.get("simulation_days"),
                    strategy_type=payload.get("strategy_type", "accumulator"),
                    use_llm=payload.get("use_llm", False),
                )
                api_deps.logger.info("✓ Simulação concluída!")
            except Exception as exc:
                api_deps.logger.exception("❌ Erro na simulação: %s", exc)
            finally:
                api_deps._SIMULATION_RUNNING = False

        asyncio.create_task(run_in_threadpool(run_and_mark_done))
        return {
            "status": "started",
            "message": "Simulação iniciada em background. Aguarde alguns segundos para ver os resultados.",
        }

    return router
