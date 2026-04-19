"""PostgreSQL-backed repository adapter for simulation workflows."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.src.data import pipeline, storage


class PostgresSimulationRepository:
    """Repository adapter that encapsulates calls to legacy storage modules."""

    def get_klines(self, table_name: str, limit: int | None = None) -> pd.DataFrame:
        return storage.get_data_from_db(table_name, limit=limit)

    def get_latest_simulation_summary(self) -> dict[str, Any] | None:
        return storage.get_latest_simulation_summary()

    def get_positions(
        self,
        include_open: bool = True,
        include_closed: bool = True,
    ) -> pd.DataFrame:
        return pipeline.get_positions_from_db(include_open=include_open, include_closed=include_closed)

    def get_predictions(self) -> pd.DataFrame:
        return pipeline.get_predictions_from_db()

    def clear_simulation_data(self) -> None:
        storage.clear_simulation_data()

    def clear_predictions_data(self) -> None:
        storage.clear_predictions_data()

    def save_predictions(self, df: pd.DataFrame) -> None:
        storage.save_predictions_to_db(df)

    def save_trades(self, trades_list: list[dict[str, Any]], current_price: float = 0.0) -> None:
        storage.save_trades(trades_list, current_price=current_price)

    def save_simulation_summary(self, **kwargs: Any) -> None:
        storage.save_simulation_summary(**kwargs)


default_simulation_repository = PostgresSimulationRepository()

