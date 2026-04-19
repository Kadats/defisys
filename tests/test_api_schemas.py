from backend.src.interfaces.api.schemas import (
    PaperRuntimeStartRequest,
    PaperRuntimeTickRequest,
    SandboxRunRequest,
    SimulationRunRequest,
)


def test_simulation_run_request_defaults():
    payload = SimulationRunRequest()
    assert payload.start_date is None
    assert payload.end_date is None
    assert payload.initial_capital is None
    assert payload.simulation_days is None
    assert payload.strategy_type == "accumulator"
    assert payload.use_llm is False


def test_sandbox_run_request_required_fields():
    payload = SandboxRunRequest(
        ai_confidence=0.8,
        initial_capital=5000.0,
        train_window=120,
        test_window=30,
    )
    assert payload.ai_confidence == 0.8
    assert payload.initial_capital == 5000.0
    assert payload.train_window == 120
    assert payload.test_window == 30


def test_paper_runtime_start_request_defaults():
    payload = PaperRuntimeStartRequest()
    assert payload.strategy_name == "accumulator"
    assert payload.environment == "paper"


def test_paper_runtime_tick_request_defaults():
    payload = PaperRuntimeTickRequest(price=65000.0)
    assert payload.symbol == "BTCUSDT"
    assert payload.source_status == "real"
    assert payload.ml_confidence == 0.5
    assert payload.health_factor == 2.0
    assert payload.kill_switch_active is False
