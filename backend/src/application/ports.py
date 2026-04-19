"""Application ports for persistence and external integrations."""

from __future__ import annotations

from typing import Any, Protocol

import pandas as pd


class SimulationRepositoryPort(Protocol):
    """Persistence contract for simulation and analytics reads/writes."""

    def get_klines(self, table_name: str, limit: int | None = None) -> pd.DataFrame:
        ...

    def get_latest_simulation_summary(self) -> dict[str, Any] | None:
        ...

    def get_positions(
        self,
        include_open: bool = True,
        include_closed: bool = True,
    ) -> pd.DataFrame:
        ...

    def get_predictions(self) -> pd.DataFrame:
        ...

    def clear_simulation_data(self) -> None:
        ...

    def clear_predictions_data(self) -> None:
        ...

    def save_predictions(self, df: pd.DataFrame) -> None:
        ...

    def save_trades(self, trades_list: list[dict[str, Any]], current_price: float = 0.0) -> None:
        ...

    def save_simulation_summary(self, **kwargs: Any) -> None:
        ...


class MarketDataGatewayPort(Protocol):
    """External data collection contract used by pipeline orchestration."""

    def fetch_all_klines(
        self,
        symbol: str,
        interval: str,
        start_timestamp: int,
        end_timestamp: int,
        max_klines_per_request: int,
        binance_api_base_url: str,
    ) -> pd.DataFrame:
        ...

    def get_fear_and_greed_index(
        self,
        limit: int,
        start_date_unix_sec: int,
        fng_api_url: str,
    ) -> list[dict[str, Any]]:
        ...

    def get_bitcoin_network_fees(self, blockchair_api_url: str) -> dict[str, Any] | None:
        ...

    def get_funding_rate_history(
        self,
        symbol: str,
        limit: int,
        start_time_ms: int,
        end_time_ms: int,
        binance_futures_api_base_url: str,
    ) -> list[dict[str, Any]]:
        ...

    def get_open_interest_history(
        self,
        symbol: str,
        period: str,
        limit: int,
        start_time_ms: int,
        end_time_ms: int,
        binance_futures_api_base_url: str,
    ) -> list[dict[str, Any]]:
        ...

    def get_implied_volatility_history(
        self,
        start_timestamp_ms: int,
        deribit_base_url: str,
    ) -> list[dict[str, Any]]:
        ...

    def get_uniswap_pool_daily_data(
        self,
        pool_id: str,
        start_timestamp_ms: int,
        thegraph_base_url: str,
        thegraph_api_key: str,
        thegraph_subgraph_ids: dict[str, str],
        default_network: str,
    ) -> list[dict[str, Any]]:
        ...


class TradingWorkflowPort(Protocol):
    """Application workflow contract for training, simulation, and runtime orchestration."""

    def train_model(self) -> dict[str, Any]:
        ...

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
        ...

    def run_trading_system(self) -> dict[str, Any]:
        ...
