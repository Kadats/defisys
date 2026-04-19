from backend.src.application import TradingWorkflowUseCases


def test_trading_workflow_use_cases_delegates_calls():
    called = {
        "train": False,
        "sim": None,
        "run": False,
    }

    def _train():
        called["train"] = True
        return {"ok": True}

    def _sim(**kwargs):
        called["sim"] = kwargs
        return {"simulation": "ok"}

    def _run():
        called["run"] = True
        return {"run": "ok"}

    use_cases = TradingWorkflowUseCases(
        train_model_fn=_train,
        run_simulation_fn=_sim,
        run_system_fn=_run,
    )

    assert use_cases.train_model() == {"ok": True}
    assert called["train"] is True

    simulation_result = use_cases.run_simulation(
        start_date="2026-01-01",
        end_date="2026-02-01",
        initial_capital=1234.5,
        backtest_days=20,
        strategy_type="accumulator",
        use_llm=True,
    )
    assert simulation_result == {"simulation": "ok"}
    assert called["sim"]["start_date"] == "2026-01-01"
    assert called["sim"]["end_date"] == "2026-02-01"
    assert called["sim"]["initial_capital"] == 1234.5
    assert called["sim"]["backtest_days"] == 20
    assert called["sim"]["strategy_type"] == "accumulator"
    assert called["sim"]["use_llm"] is True

    assert use_cases.run_trading_system() == {"run": "ok"}
    assert called["run"] is True

