import pandas as pd

from backend.src.infrastructure.gateways.market_data_gateway import HttpMarketDataGateway
from backend.src.infrastructure.repositories.simulation_repository import PostgresSimulationRepository


def test_simulation_repository_delegates_reads(monkeypatch):
    repo = PostgresSimulationRepository()

    klines_df = pd.DataFrame({"Open_time": [pd.Timestamp("2026-01-01")]})
    positions_df = pd.DataFrame({"id": [1]})
    predictions_df = pd.DataFrame({"prediction": [1]})

    monkeypatch.setattr(
        "backend.src.data.storage.get_data_from_db",
        lambda table_name, limit=None: klines_df,
    )
    monkeypatch.setattr(
        "backend.src.data.storage.get_latest_simulation_summary",
        lambda: {"id": 10},
    )
    monkeypatch.setattr(
        "backend.src.data.pipeline.get_positions_from_db",
        lambda include_open=True, include_closed=True: positions_df,
    )
    monkeypatch.setattr(
        "backend.src.data.pipeline.get_predictions_from_db",
        lambda: predictions_df,
    )

    assert repo.get_klines("btcusdt_4h_klines", limit=10).equals(klines_df)
    assert repo.get_latest_simulation_summary() == {"id": 10}
    assert repo.get_positions(include_open=False, include_closed=True).equals(positions_df)
    assert repo.get_predictions().equals(predictions_df)


def test_simulation_repository_delegates_writes(monkeypatch):
    repo = PostgresSimulationRepository()
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        "backend.src.data.storage.clear_simulation_data",
        lambda: calls.setdefault("clear_simulation_data", True),
    )
    monkeypatch.setattr(
        "backend.src.data.storage.clear_predictions_data",
        lambda: calls.setdefault("clear_predictions_data", True),
    )
    monkeypatch.setattr(
        "backend.src.data.storage.save_predictions_to_db",
        lambda df: calls.setdefault("save_predictions_to_db", len(df)),
    )
    monkeypatch.setattr(
        "backend.src.data.storage.save_trades",
        lambda trades, current_price=0.0: calls.setdefault(
            "save_trades",
            (len(trades), current_price),
        ),
    )
    monkeypatch.setattr(
        "backend.src.data.storage.save_simulation_summary",
        lambda **kwargs: calls.setdefault("save_simulation_summary", kwargs["strategy_used"]),
    )

    repo.clear_simulation_data()
    repo.clear_predictions_data()
    repo.save_predictions(pd.DataFrame({"prediction": [1, 0, 1]}))
    repo.save_trades([{"action": "BUY"}], current_price=100.0)
    repo.save_simulation_summary(strategy_used="accumulator")

    assert calls["clear_simulation_data"] is True
    assert calls["clear_predictions_data"] is True
    assert calls["save_predictions_to_db"] == 3
    assert calls["save_trades"] == (1, 100.0)
    assert calls["save_simulation_summary"] == "accumulator"


def test_market_data_gateway_delegates_sources(monkeypatch):
    gateway = HttpMarketDataGateway()

    klines_df = pd.DataFrame({"Open_time": [pd.Timestamp("2026-01-01")]})
    monkeypatch.setattr("backend.src.data.sources.fetch_all_klines", lambda *args, **kwargs: klines_df)
    monkeypatch.setattr(
        "backend.src.data.sources.get_fear_and_greed_index",
        lambda **kwargs: [{"value": "54"}],
    )
    monkeypatch.setattr(
        "backend.src.data.sources.get_bitcoin_network_fees",
        lambda **kwargs: {"average_transaction_fee_24h": 2.5},
    )

    assert gateway.fetch_all_klines("BTCUSDT", "4h", 1, 2, 1000, "https://api.binance.com").equals(klines_df)
    assert gateway.get_fear_and_greed_index(10, 100, "https://fng").pop()["value"] == "54"
    assert gateway.get_bitcoin_network_fees("https://blockchair")["average_transaction_fee_24h"] == 2.5
