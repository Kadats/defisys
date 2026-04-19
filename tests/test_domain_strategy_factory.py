import pytest

from backend.src.domain.strategies import build_strategy


def test_build_strategy_returns_configured_builder_instance():
    class DummyStrategy:
        def __init__(self, use_llm: bool) -> None:
            self.use_llm = use_llm

    strategy = build_strategy(
        "accumulator",
        use_llm=True,
        strategy_builders={
            "accumulator": lambda flag: DummyStrategy(use_llm=flag),
        },
    )

    assert isinstance(strategy, DummyStrategy)
    assert strategy.use_llm is True


def test_build_strategy_raises_with_available_options():
    with pytest.raises(ValueError) as exc_info:
        build_strategy(
            "unknown",
            use_llm=False,
            strategy_builders={
                "accumulator": lambda _flag: object(),
                "swing_usd": lambda _flag: object(),
            },
        )

    assert "Unknown strategy type: unknown" in str(exc_info.value)
    assert "accumulator, swing_usd" in str(exc_info.value)
