import pandas as pd
import pytest

from backend.src import system_runner
import backend.src.data.pipeline as data_pipeline


def _make_market_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open_time": [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")],
            "Close": [100.0, 110.0],
        }
    )


def _make_predictions_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open_time": [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")],
            "prediction": [1, 0],
            "prediction_proba": [0.7, 0.4],
        }
    )


class DummyEngine:
    last_instance = None

    def __init__(self, initial_capital_usd: float = 1000.0) -> None:
        DummyEngine.last_instance = self
        self.initial_capital = initial_capital_usd
        self.usd_balance = initial_capital_usd
        self.btc_hodl_balance = 0.0
        self.total_debt_usd = 0.0
        self.health_factor = 999.0
        self.active_lps = []
        self.transaction_log = []
        self.last_strategy = None

    def run(self, df: pd.DataFrame, strategy) -> dict:
        self.last_strategy = strategy
        return {}

    def _get_lp_value(self, lp, price: float):
        return 0.0, 0.0, 0.0


class DummyAccumulatorStrategy:
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm


class DummyBTCLiteStrategy:
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm


@pytest.fixture
def patch_simulation_dependencies(monkeypatch):
    monkeypatch.setattr(system_runner, "TradingEngine", DummyEngine)
    monkeypatch.setattr(system_runner, "AccumulatorStrategy", DummyAccumulatorStrategy)
    monkeypatch.setattr(system_runner, "BTCLiteStrategy", DummyBTCLiteStrategy)
    monkeypatch.setattr(system_runner.storage, "clear_simulation_data", lambda: None)
    monkeypatch.setattr(system_runner, "save_trades", lambda *args, **kwargs: None)
    monkeypatch.setattr(system_runner, "save_simulation_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(data_pipeline, "get_predictions_from_db", lambda: _make_predictions_df())
    monkeypatch.setattr(data_pipeline, "get_full_prepared_data", lambda: _make_market_df())


@pytest.mark.usefixtures("patch_simulation_dependencies")
def test_strategy_factory_accumulator():
    result = system_runner.run_simulation(strategy_type="accumulator")

    assert "backtest_report" in result
    assert isinstance(DummyEngine.last_instance.last_strategy, DummyAccumulatorStrategy)


@pytest.mark.usefixtures("patch_simulation_dependencies")
def test_strategy_factory_btc_lite():
    result = system_runner.run_simulation(strategy_type="btc_lite")

    assert "backtest_report" in result
    assert isinstance(DummyEngine.last_instance.last_strategy, DummyBTCLiteStrategy)


@pytest.mark.usefixtures("patch_simulation_dependencies")
def test_strategy_factory_swing_usd_not_implemented():
    result = system_runner.run_simulation(strategy_type="swing_usd")

    assert "backtest_report" in result
    assert "not implemented" in result["backtest_report"]["error"].lower()


@pytest.mark.usefixtures("patch_simulation_dependencies")
def test_strategy_factory_unknown_strategy():
    result = system_runner.run_simulation(strategy_type="unknown")

    assert "backtest_report" in result
    assert "unknown strategy type" in result["backtest_report"]["error"].lower()
