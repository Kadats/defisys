"""Paper trading runtime routes."""

from fastapi import APIRouter, HTTPException, Query

from backend.src.interfaces.api.schemas import PaperRuntimeStartRequest, PaperRuntimeTickRequest
from backend.src.services.paper_runtime import paper_runtime

router = APIRouter(tags=["Paper Runtime"])


@router.post("/api/paper/runtime/start")
def start_paper_runtime(payload: PaperRuntimeStartRequest):
    session = paper_runtime.start_session(
        strategy_name=payload.strategy_name,
        environment=payload.environment,
    )
    return {"status": "started", "session": session.__dict__}


@router.post("/api/paper/runtime/stop")
def stop_paper_runtime():
    session = paper_runtime.stop_session()
    if session is None:
        return {"status": "not_running"}
    return {"status": "stopped", "session": session.__dict__}


@router.post("/api/paper/runtime/tick")
def ingest_paper_runtime_tick(payload: PaperRuntimeTickRequest):
    try:
        result = paper_runtime.ingest_market_snapshot(
            symbol=payload.symbol,
            price=payload.price,
            source_status=payload.source_status,
            ml_confidence=payload.ml_confidence,
            health_factor=payload.health_factor,
            kill_switch_active=payload.kill_switch_active,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "processed", "result": result}


@router.get("/api/paper/runtime/status")
def get_paper_runtime_status():
    return paper_runtime.get_status()


@router.get("/api/paper/runtime/events")
def get_paper_runtime_events(limit: int = Query(default=100, ge=1, le=1000)):
    return {"events": paper_runtime.list_events(limit=limit)}


@router.get("/api/paper/runtime/alerts")
def get_paper_runtime_alerts(
    active_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
):
    return {"alerts": paper_runtime.list_alerts(active_only=active_only, limit=limit)}
