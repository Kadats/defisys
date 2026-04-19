"""Request/response schemas for API endpoints."""

from pydantic import BaseModel


class SimulationRunRequest(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    initial_capital: float | None = None
    simulation_days: int | None = None
    strategy_type: str = "accumulator"
    use_llm: bool = False


class SandboxRunRequest(BaseModel):
    ai_confidence: float
    initial_capital: float
    train_window: int
    test_window: int


class PaperRuntimeStartRequest(BaseModel):
    strategy_name: str = "accumulator"
    environment: str = "paper"


class PaperRuntimeTickRequest(BaseModel):
    symbol: str = "BTCUSDT"
    price: float
    source_status: str = "real"
    ml_confidence: float = 0.5
    health_factor: float = 2.0
    kill_switch_active: bool = False
