"""Application use cases for orchestration-level workflows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .ports import TradingWorkflowPort


class _CallableTradingWorkflow:
    def __init__(
        self,
        train_model_fn: Callable[[], dict[str, Any]],
        run_simulation_fn: Callable[..., dict[str, Any]],
        run_system_fn: Callable[[], dict[str, Any]],
    ) -> None:
        self._train_model_fn = train_model_fn
        self._run_simulation_fn = run_simulation_fn
        self._run_system_fn = run_system_fn

    def train_model(self) -> dict[str, Any]:
        return self._train_model_fn()

    def run_simulation(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        initial_capital: float | None = None,
        backtest_days: int | None = None,
        strategy_type: str = "accumulator",
        use_llm: bool = False,
    ) -> dict[str, Any]:
        return self._run_simulation_fn(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            backtest_days=backtest_days,
            strategy_type=strategy_type,
            use_llm=use_llm,
        )

    def run_trading_system(self) -> dict[str, Any]:
        return self._run_system_fn()


class TradingWorkflowUseCases:
    """Use-case facade for training, simulation, and full system runs."""

    def __init__(self, workflow: TradingWorkflowPort) -> None:
        self._workflow = workflow

    @classmethod
    def from_callables(
        cls,
        train_model_fn: Callable[[], dict[str, Any]],
        run_simulation_fn: Callable[..., dict[str, Any]],
        run_system_fn: Callable[[], dict[str, Any]],
    ) -> "TradingWorkflowUseCases":
        return cls(
            _CallableTradingWorkflow(
                train_model_fn=train_model_fn,
                run_simulation_fn=run_simulation_fn,
                run_system_fn=run_system_fn,
            )
        )

    def train_model(self) -> dict[str, Any]:
        return self._workflow.train_model()

    def run_simulation(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        initial_capital: float | None = None,
        backtest_days: int | None = None,
        strategy_type: str = "accumulator",
        use_llm: bool = False,
    ) -> dict[str, Any]:
        return self._workflow.run_simulation(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            backtest_days=backtest_days,
            strategy_type=strategy_type,
            use_llm=use_llm,
        )

    def run_trading_system(self) -> dict[str, Any]:
        return self._workflow.run_trading_system()
