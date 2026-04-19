"""Routers for dashboard and analytics endpoints."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from fastapi import APIRouter, HTTPException


def create_dashboard_router(api_deps) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/api/v1/summary",
        tags=["Dashboard"],
        summary="Get Backtest Summary",
        description="Returns the official backtest summary from database, including strategy returns, BTC HODL benchmark, ML accuracy, and win rate.",
    )
    def get_summary():
        official_summary = api_deps.get_latest_simulation_summary()
        if official_summary:
            api_deps.logger.info("✓ Using OFFICIAL summary from database")
            positions_df = api_deps.get_positions_from_db(
                include_open=False, include_closed=True
            )
            win_rate = 0.0
            if not positions_df.empty:
                wins = positions_df[positions_df["final_profit_usd"] > 0]
                win_rate = len(wins) / len(positions_df)

            preds_df = api_deps.get_predictions_from_db()
            accuracy = 0.0
            current_action = "AGUARDAR"
            if not preds_df.empty and "prediction_correct" in preds_df.columns:
                try:
                    preds_df["prediction_correct"] = pd.to_numeric(
                        preds_df["prediction_correct"], errors="coerce"
                    )
                except Exception as exc:
                    api_deps.logger.warning(
                        "Error converting prediction_correct to numeric: %s", exc
                    )
                valid_predictions = preds_df["prediction_correct"].dropna()
                if len(valid_predictions) > 0:
                    accuracy = float(valid_predictions.astype(float).mean())

                if "prediction" in preds_df.columns and len(preds_df) > 0:
                    last_pred = preds_df.iloc[-1]["prediction"]
                    if last_pred == 1:
                        current_action = "COMPRAR"

            summary_data = {
                "initial_capital": official_summary.get("initial_capital", 0),
                "final_capital": official_summary.get("total_equity", 0),
                "net_profit": official_summary.get("total_equity", 0)
                - official_summary.get("initial_capital", 0),
                "strategy_return_pct": official_summary.get("roi_percent", 0),
                "btc_hodl_return_pct": official_summary.get("benchmark_roi_percent", 0),
                "win_rate": win_rate,
                "ml_accuracy": accuracy,
                "current_action": current_action,
                "backtest_start_date": None,
                "backtest_end_date": None,
                "last_updated": official_summary.get(
                    "timestamp", datetime.now().isoformat()
                ),
            }
            api_deps._SUMMARY_CACHE = api_deps.sanitize_for_json(summary_data)
            return api_deps._SUMMARY_CACHE

        api_deps.logger.info(
            "No official summary found. Running run_trading_system() to generate one..."
        )
        if api_deps._SUMMARY_CACHE:
            return api_deps._SUMMARY_CACHE

        try:
            result = api_deps.run_trading_system()
            report = result.get("backtest_report", {})
            if "error" in report:
                raise HTTPException(status_code=500, detail=report["error"])

            positions_df = api_deps.get_positions_from_db(
                include_open=False, include_closed=True
            )
            win_rate = 0.0
            if not positions_df.empty:
                wins = positions_df[positions_df["final_profit_usd"] > 0]
                win_rate = len(wins) / len(positions_df)

            preds_df = api_deps.get_predictions_from_db()
            accuracy = 0.0
            current_action = "AGUARDAR"
            if not preds_df.empty and "prediction_correct" in preds_df.columns:
                try:
                    preds_df["prediction_correct"] = pd.to_numeric(
                        preds_df["prediction_correct"], errors="coerce"
                    )
                except Exception as exc:
                    api_deps.logger.warning(
                        "Error converting prediction_correct to numeric: %s", exc
                    )
                valid_predictions = preds_df["prediction_correct"].dropna()
                api_deps.logger.info(
                    "ML Accuracy: %s valid rows of %s total for calculation",
                    len(valid_predictions),
                    len(preds_df),
                )
                if len(valid_predictions) > 0:
                    accuracy = float(valid_predictions.astype(float).mean())
                if "prediction" in preds_df.columns and len(preds_df) > 0:
                    last_pred = preds_df.iloc[-1]["prediction"]
                    if last_pred == 1:
                        current_action = "COMPRAR"

            summary_data = {
                "initial_capital": report.get("initial_capital_usd", 0),
                "final_capital": report.get("final_usd_value", 0),
                "net_profit": report.get("profit_usd", 0),
                "strategy_return_pct": report.get("profit_percentage_usd", 0),
                "btc_hodl_return_pct": report.get("btc_benchmark_profit_percentage", 0),
                "win_rate": win_rate,
                "ml_accuracy": accuracy,
                "current_action": current_action,
                "backtest_start_date": report.get("start_date"),
                "backtest_end_date": report.get("end_date"),
                "last_updated": datetime.now().isoformat(),
            }
            api_deps._SUMMARY_CACHE = api_deps.sanitize_for_json(summary_data)
            return api_deps._SUMMARY_CACHE
        except Exception as exc:
            api_deps.logger.exception("Erro crítico ao gerar resumo: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    @router.get(
        "/api/v1/trade_history",
        tags=["Dashboard"],
        summary="Get Transaction Log",
        description="Returns the detailed transaction log of all trades, harvests, and rebalancing actions from the backtest.",
    )
    def get_trade_history():
        api_deps.logger.info("Fetching trade history from backtest results...")
        try:
            if not api_deps._SUMMARY_CACHE:
                api_deps.logger.info(
                    "Cache vazio. Rodando run_trading_system() para gerar histórico..."
                )
                result = api_deps.run_trading_system()
                report = result.get("backtest_report", {})
                if "error" in report:
                    raise HTTPException(status_code=500, detail=report["error"])
                api_deps._SUMMARY_CACHE = api_deps.sanitize_for_json(
                    {
                        "initial_capital": report.get("initial_capital_usd", 0),
                        "final_capital": report.get("final_usd_value", 0),
                        "net_profit": report.get("profit_usd", 0),
                        "strategy_return_pct": report.get("profit_percentage_usd", 0),
                        "btc_hodl_return_pct": report.get(
                            "btc_benchmark_profit_percentage", 0
                        ),
                        "win_rate": 0.0,
                        "ml_accuracy": 0.0,
                        "current_action": "AGUARDAR",
                        "backtest_start_date": report.get("start_date"),
                        "backtest_end_date": report.get("end_date"),
                        "last_updated": datetime.now().isoformat(),
                    }
                )

            result = api_deps.run_trading_system()
            backtest_result = result.get("backtest_report", {})
            transaction_log = backtest_result.get("transaction_log", [])

            transaction_history = []
            for trans in transaction_log:
                timestamp = trans.get("timestamp")
                if isinstance(timestamp, pd.Timestamp):
                    timestamp_str = timestamp.isoformat()
                elif hasattr(timestamp, "isoformat"):
                    timestamp_str = timestamp.isoformat()
                else:
                    timestamp_str = str(timestamp)
                transaction_history.append(
                    {
                        "timestamp": timestamp_str,
                        "action": trans.get("action", ""),
                        "btc_price": float(trans.get("btc_price", 0)),
                        "usd_amount": float(trans.get("usd_amount", 0)),
                        "btc_amount": float(trans.get("btc_amount", 0)),
                        "fee_usd": float(trans.get("fee_usd", 0)),
                        "pnl_usd": float(trans.get("pnl_usd", 0)),
                        "details": trans.get("details", ""),
                    }
                )

            total_gas_paid = sum(t.get("fee_usd", 0) for t in transaction_history)
            return {
                "transactions": api_deps.sanitize_for_json(transaction_history),
                "total_gas_paid": total_gas_paid,
                "total_transactions": len(transaction_history),
            }
        except Exception as exc:
            api_deps.logger.exception("Erro ao buscar transaction history: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    @router.get(
        "/api/v1/chart_data",
        tags=["Market Data"],
        summary="Get Klines (OHLCV Data)",
        description="Returns historical candlestick data (Open, High, Low, Close, Volume) for charting. Supports optional date filtering via 'start' and 'end' parameters. Default limit is 1000 candles.",
    )
    def get_chart_data(start: str = None, end: str = None):
        try:
            klines_table_name = (
                f"{api_deps.DEFAULT_SYMBOL}_{api_deps.DEFAULT_INTERVAL}_klines".lower()
            )
            df_klines = api_deps.get_data_from_db(
                klines_table_name, limit=api_deps.DEFAULT_KLINES_LIMIT
            )
            if df_klines.empty:
                return []

            if start is not None or end is not None:
                try:
                    if "Open_time" in df_klines.columns:
                        df_klines["Open_time"] = pd.to_datetime(df_klines["Open_time"])
                        if start is not None:
                            start_date = pd.to_datetime(start)
                            df_klines = df_klines[df_klines["Open_time"] >= start_date]
                        if end is not None:
                            end_date = pd.to_datetime(end)
                            df_klines = df_klines[df_klines["Open_time"] <= end_date]
                except Exception as exc:
                    api_deps.logger.warning(
                        "Error filtering chart data by dates: %s. Returning unfiltered data.",
                        exc,
                    )

            return api_deps.sanitize_df_for_json(df_klines)
        except Exception as exc:
            api_deps.logger.exception("Erro ao buscar chart_data: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    @router.get(
        "/api/v1/backtest_period",
        tags=["Dashboard"],
        summary="Get Backtest Period",
        description="Returns the start and end dates of the most recent backtest execution. Useful for syncing frontend chart zoom with backtest window.",
    )
    def get_backtest_period():
        try:
            if api_deps._SUMMARY_CACHE:
                return {
                    "start_date": api_deps._SUMMARY_CACHE.get("backtest_start_date"),
                    "end_date": api_deps._SUMMARY_CACHE.get("backtest_end_date"),
                }

            result = api_deps.run_trading_system()
            report = result.get("backtest_report", {})
            return {
                "start_date": report.get("start_date"),
                "end_date": report.get("end_date"),
            }
        except Exception as exc:
            api_deps.logger.exception("Erro ao buscar backtest_period: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    @router.get(
        "/api/v1/market_analysis",
        tags=["Market Data"],
        summary="Get Market X-Ray",
        description="Returns volatility metrics and analysis grouped by year. Includes total return, max drawdown, explosive days (>5%), severe dumps (<-5%), and daily return distribution. Essential for understanding market behavior patterns.",
    )
    def get_market_analysis():
        try:
            klines_table_name = (
                f"{api_deps.DEFAULT_SYMBOL}_{api_deps.DEFAULT_INTERVAL}_klines".lower()
            )
            df_klines = api_deps.get_data_from_db(klines_table_name, limit=None)
            if df_klines.empty:
                api_deps.logger.warning("No klines data available for market analysis.")
                return {}

            yearly_metrics = api_deps.calculate_yearly_metrics(df_klines)
            metrics_str_keys = {str(k): v for k, v in yearly_metrics.items()}
            return api_deps.sanitize_for_json(metrics_str_keys)
        except Exception as exc:
            api_deps.logger.exception("Erro ao analisar mercado: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    @router.get(
        "/api/v1/positions",
        tags=["Execution"],
        summary="Get Trading Positions",
        description="Returns open and closed trading positions with profit/loss details. Used to track position history and validate strategy execution.",
    )
    def get_positions():
        try:
            df = api_deps.get_positions_from_db()
            if df.empty:
                return {"open_positions": [], "closed_positions": []}
            open_df = df[df["close_timestamp"].isnull()]
            closed_df = df[df["close_timestamp"].notnull()]
            return {
                "open_positions": api_deps.sanitize_df_for_json(open_df),
                "closed_positions": api_deps.sanitize_df_for_json(closed_df),
            }
        except Exception as exc:
            api_deps.logger.exception("Erro positions: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    return router
