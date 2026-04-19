"""Strategy factory for simulation runtime."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


StrategyBuilder = Callable[[bool], Any]


def build_strategy(
    strategy_type: str,
    *,
    use_llm: bool,
    strategy_builders: Mapping[str, StrategyBuilder],
) -> Any:
    """Instantiate a strategy from the canonical strategy name."""
    builder = strategy_builders.get(strategy_type)
    if builder is None:
        available = ", ".join(sorted(strategy_builders.keys()))
        raise ValueError(
            f"Unknown strategy type: {strategy_type}. Available: {available}"
        )
    return builder(use_llm)
