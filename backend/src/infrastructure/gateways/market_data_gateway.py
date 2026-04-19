"""HTTP gateway adapter for market data sources."""

from __future__ import annotations

from typing import Any

import pandas as pd

from backend.src.data import sources


class HttpMarketDataGateway:
    """Gateway adapter that wraps external collectors from data.sources."""

    def fetch_all_klines(
        self,
        symbol: str,
        interval: str,
        start_timestamp: int,
        end_timestamp: int,
        max_klines_per_request: int,
        binance_api_base_url: str,
    ) -> pd.DataFrame:
        return sources.fetch_all_klines(
            symbol,
            interval,
            start_timestamp,
            end_timestamp,
            max_klines_per_request=max_klines_per_request,
            binance_api_base_url=binance_api_base_url,
        )

    def get_fear_and_greed_index(
        self,
        limit: int,
        start_date_unix_sec: int,
        fng_api_url: str,
    ) -> list[dict[str, Any]]:
        return sources.get_fear_and_greed_index(
            limit=limit,
            start_date_unix_sec=start_date_unix_sec,
            fng_api_url=fng_api_url,
        )

    def get_bitcoin_network_fees(self, blockchair_api_url: str) -> dict[str, Any] | None:
        return sources.get_bitcoin_network_fees(blockchair_api_url=blockchair_api_url)

    def get_funding_rate_history(
        self,
        symbol: str,
        limit: int,
        start_time_ms: int,
        end_time_ms: int,
        binance_futures_api_base_url: str,
    ) -> list[dict[str, Any]]:
        return sources.get_funding_rate_history(
            symbol,
            limit=limit,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            binance_futures_api_base_url=binance_futures_api_base_url,
        )

    def get_open_interest_history(
        self,
        symbol: str,
        period: str,
        limit: int,
        start_time_ms: int,
        end_time_ms: int,
        binance_futures_api_base_url: str,
    ) -> list[dict[str, Any]]:
        return sources.get_open_interest_history(
            symbol,
            period=period,
            limit=limit,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            binance_futures_api_base_url=binance_futures_api_base_url,
        )

    def get_implied_volatility_history(
        self,
        start_timestamp_ms: int,
        deribit_base_url: str,
    ) -> list[dict[str, Any]]:
        return sources.get_implied_volatility_history(
            start_timestamp_ms=start_timestamp_ms,
            deribit_base_url=deribit_base_url,
        )

    def get_uniswap_pool_daily_data(
        self,
        pool_id: str,
        start_timestamp_ms: int,
        thegraph_base_url: str,
        thegraph_api_key: str,
        thegraph_subgraph_ids: dict[str, str],
        default_network: str,
    ) -> list[dict[str, Any]]:
        return sources.get_uniswap_pool_daily_data(
            pool_id=pool_id,
            start_timestamp_ms=start_timestamp_ms,
            thegraph_base_url=thegraph_base_url,
            thegraph_api_key=thegraph_api_key,
            thegraph_subgraph_ids=thegraph_subgraph_ids,
            default_network=default_network,
        )


default_market_data_gateway = HttpMarketDataGateway()

