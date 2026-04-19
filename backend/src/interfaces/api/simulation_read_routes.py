"""Routers for simulation/history read endpoints."""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.src.data import storage
from backend.src.services.analytics import get_simulation_results


def _empty_simulation_response() -> dict[str, Any]:
    return {
        "kpis": {
            "total_trades": 0,
            "initial_balance": 1000.0,
            "final_balance": 1000.0,
            "roi": 0.0,
            "benchmark_roi": 0.0,
        },
        "trades": [],
        "summary": {
            "total_trades": 0,
            "initial_capital": 1000.0,
            "total_equity": 1000.0,
            "roi_percent": 0.0,
            "benchmark_roi_percent": 0.0,
            "wallet_spot_usd": 0.0,
            "wallet_spot_btc": 0.0,
            "wallet_spot_total_usd": 0.0,
            "wallet_lp_value_usd": 0.0,
            "lp_active_count": 0,
            "lp_fees_usd": 0.0,
            "aave_collateral_usd": 0.0,
            "aave_debt_usd": 0.0,
            "aave_health_factor": 0.0,
            "alpha_vs_hold": 0.0,
            "initial_token_balance": 0.0,
            "final_token_balance": 0.0,
            "token_roi": 0.0,
        },
    }


def _get_health_factor_status(health_factor: float) -> str:
    if health_factor >= 1.5:
        return "SAFE"
    if health_factor >= 1.2:
        return "WARNING"
    if health_factor > 0:
        return "DANGER"
    return "LIQUIDATED"


def create_simulation_read_router(api_deps) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/api/history",
        tags=["Market Data"],
        summary="Get Klines History",
        description="Returns OHLCV candles for charting from btcusdt_4h_klines.",
    )
    def get_history():
        conn = None
        try:
            conn = storage.create_connection()
            if not conn:
                raise HTTPException(status_code=500, detail="Database connection failed")

            query = (
                "SELECT open_time AS time, open, high, low, close, volume "
                "FROM btcusdt_4h_klines ORDER BY open_time ASC"
            )
            df = pd.read_sql(query, conn)
            if df.empty:
                return []

            df["time"] = pd.to_datetime(df["time"], unit="ms")
            return api_deps.sanitize_for_json(df.to_dict(orient="records"))
        except HTTPException:
            raise
        except Exception as exc:
            api_deps.logger.exception("Erro ao buscar history: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    @router.get(
        "/api/simulation",
        tags=["Simulation"],
        summary="Get Simulation Results",
        description="Returns simulation KPIs, official summary, and trade history.",
    )
    def get_simulation():
        try:
            results = get_simulation_results()
            if results.get("trades"):
                results["trades"] = sorted(
                    results["trades"],
                    key=lambda item: item.get("date", ""),
                    reverse=True,
                )

            official_summary = api_deps.get_latest_simulation_summary()
            if official_summary:
                kpis = {
                    "total_trades": official_summary.get(
                        "total_trades", results["kpis"]["total_trades"]
                    ),
                    "initial_balance": official_summary.get(
                        "initial_capital", results["kpis"]["initial_balance"]
                    ),
                    "final_balance": official_summary.get(
                        "total_equity", results["kpis"]["final_balance"]
                    ),
                    "roi": official_summary.get("roi_percent", results["kpis"]["roi"]),
                    "benchmark_roi": official_summary.get(
                        "benchmark_roi_percent", results["kpis"]["benchmark_roi"]
                    ),
                }
                summary = {
                    "total_trades": official_summary.get("total_trades"),
                    "initial_capital": official_summary.get("initial_capital"),
                    "total_equity": official_summary.get("total_equity"),
                    "roi_percent": official_summary.get("roi_percent"),
                    "benchmark_roi_percent": official_summary.get("benchmark_roi_percent"),
                    "wallet_spot_usd": official_summary.get("cash_balance"),
                    "wallet_spot_btc": official_summary.get("btc_amount"),
                    "wallet_spot_total_usd": (
                        official_summary.get("cash_balance", 0)
                        + (
                            official_summary.get("btc_amount", 0)
                            * official_summary.get("btc_price_final", 0)
                        )
                    ),
                    "wallet_lp_value_usd": official_summary.get("wallet_lp_value_usd"),
                    "lp_active_count": official_summary.get("lp_active_count"),
                    "lp_fees_usd": official_summary.get("lp_fees_usd"),
                    "aave_collateral_usd": official_summary.get("aave_collateral_usd"),
                    "aave_debt_usd": official_summary.get("aave_debt_usd"),
                    "aave_health_factor": official_summary.get("aave_health_factor"),
                    "alpha_vs_hold": official_summary.get("alpha_vs_hold"),
                    "initial_token_balance": official_summary.get("initial_token_balance"),
                    "final_token_balance": official_summary.get("final_token_balance"),
                    "token_roi": official_summary.get("token_roi"),
                }
            else:
                api_deps.logger.info(
                    "✓ No official summary in DB, using calculated KPIs for summary"
                )
                kpis = results["kpis"]
                summary = {
                    "total_trades": results["kpis"]["total_trades"],
                    "initial_capital": results["kpis"]["initial_balance"],
                    "total_equity": results["kpis"]["final_balance"],
                    "roi_percent": results["kpis"]["roi"],
                    "benchmark_roi_percent": results["kpis"]["benchmark_roi"],
                    "wallet_spot_usd": 0,
                    "wallet_spot_btc": 0,
                    "wallet_spot_total_usd": 0,
                    "wallet_lp_value_usd": 0,
                    "lp_active_count": 0,
                    "lp_fees_usd": 0,
                    "aave_collateral_usd": 0,
                    "aave_debt_usd": 0,
                    "aave_health_factor": 0,
                    "alpha_vs_hold": 0,
                    "initial_token_balance": 0,
                    "final_token_balance": 0,
                    "token_roi": 0,
                }

            return api_deps.sanitize_for_json(
                {
                    "kpis": kpis,
                    "trades": results["trades"],
                    "summary": summary,
                }
            )
        except Exception as exc:
            api_deps.logger.exception("Erro ao buscar simulation results: %s", exc)
            return _empty_simulation_response()

    @router.get(
        "/api/simulation/status",
        tags=["Simulation"],
        summary="Get Simulation Status",
        description="Returns whether simulation is currently running.",
    )
    def get_simulation_status():
        try:
            official_summary = api_deps.get_latest_simulation_summary()
            return {
                "running": api_deps._SIMULATION_RUNNING,
                "has_results": official_summary is not None,
                "trades_count": official_summary.get("total_trades", 0)
                if official_summary
                else 0,
            }
        except Exception as exc:
            api_deps.logger.exception("Erro ao buscar status: %s", exc)
            return {
                "running": api_deps._SIMULATION_RUNNING,
                "has_results": False,
                "trades_count": 0,
                "error": str(exc),
            }

    @router.get(
        "/api/simulation/summary",
        tags=["Simulation"],
        summary="Get Isolated Treasuries Summary",
        description="Returns the final state of 3 distinct wallets: Spot (USD/BTC), DeFi (LPs), and AAVE (Collateral/Debt).",
    )
    def get_treasuries_summary():
        try:
            official_summary = api_deps.get_latest_simulation_summary()
            if official_summary:
                api_deps.logger.info("✓ Returning treasuries summary from database")
                response = {
                    "spot": {
                        "label": "🏦 Bot Wallet (Spot)",
                        "usd_available": official_summary.get("cash_balance", 0),
                        "btc_balance": official_summary.get("btc_amount", 0),
                        "btc_price": official_summary.get("btc_price_final", 0),
                        "total_usd": (
                            official_summary.get("cash_balance", 0)
                            + (
                                official_summary.get("btc_amount", 0)
                                * official_summary.get("btc_price_final", 0)
                            )
                        ),
                    },
                    "defi": {
                        "label": "🌾 DeFi LPs (Yield)",
                        "capital_allocated": official_summary.get("wallet_lp_value_usd", 0),
                        "active_positions": official_summary.get("lp_active_count", 0),
                        "fees_earned": official_summary.get("lp_fees_usd", 0),
                    },
                    "aave": {
                        "label": "👻 AAVE (Crédito)",
                        "collateral_btc_usd": official_summary.get("aave_collateral_usd", 0),
                        "debt_borrow_usd": official_summary.get("aave_debt_usd", 0),
                        "health_factor": official_summary.get("aave_health_factor", 0),
                        "health_status": _get_health_factor_status(
                            official_summary.get("aave_health_factor", 0)
                        ),
                    },
                    "summary": {
                        "initial_capital": official_summary.get("initial_capital", 0),
                        "total_equity": official_summary.get("total_equity", 0),
                        "roi_percent": official_summary.get("roi_percent", 0),
                        "benchmark_roi_percent": official_summary.get(
                            "benchmark_roi_percent", 0
                        ),
                    },
                }
                return api_deps.sanitize_for_json(response)

            api_deps.logger.warning("No simulation summary found. Run simulation first.")
            return {
                "spot": {
                    "label": "🏦 Bot Wallet (Spot)",
                    "usd_available": 0,
                    "btc_balance": 0,
                    "btc_price": 0,
                    "total_usd": 0,
                },
                "defi": {
                    "label": "🌾 DeFi LPs (Yield)",
                    "capital_allocated": 0,
                    "active_positions": 0,
                    "fees_earned": 0,
                },
                "aave": {
                    "label": "👻 AAVE (Crédito)",
                    "collateral_btc_usd": 0,
                    "debt_borrow_usd": 0,
                    "health_factor": 0,
                    "health_status": "NONE",
                },
                "summary": {
                    "initial_capital": 0,
                    "total_equity": 0,
                    "roi_percent": 0,
                    "benchmark_roi_percent": 0,
                },
            }
        except Exception as exc:
            api_deps.logger.exception("Erro ao buscar treasuries summary: %s", exc)
            return {
                "spot": {
                    "label": "🏦 Bot Wallet (Spot)",
                    "usd_available": 0,
                    "btc_balance": 0,
                    "btc_price": 0,
                    "total_usd": 0,
                },
                "defi": {
                    "label": "🌾 DeFi LPs (Yield)",
                    "capital_allocated": 0,
                    "active_positions": 0,
                    "fees_earned": 0,
                },
                "aave": {
                    "label": "👻 AAVE (Crédito)",
                    "collateral_btc_usd": 0,
                    "debt_borrow_usd": 0,
                    "health_factor": 0,
                    "health_status": "NONE",
                },
                "summary": {
                    "initial_capital": 0,
                    "total_equity": 0,
                    "roi_percent": 0,
                    "benchmark_roi_percent": 0,
                },
            }

    return router
