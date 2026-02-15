import logging
from typing import Any, Dict, List

import pandas as pd

from backend.src.data import storage

logger = logging.getLogger(__name__)

DEFAULT_INITIAL_BALANCE = 1000.0


def _infer_trade_type(strategy_value: Any) -> str:
    if not strategy_value:
        return "Long"
    strategy = str(strategy_value).lower()
    if "short" in strategy or "bear" in strategy:
        return "Short"
    return "Long"


def _to_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        if isinstance(value, float) and pd.isna(value):
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _format_date(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""

    if isinstance(value, (int, float)):
        dt = pd.to_datetime(int(value), unit="ms", errors="coerce")
    else:
        dt = pd.to_datetime(value, errors="coerce")

    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d")


def get_simulation_results() -> Dict[str, Any]:
    conn = storage.create_connection()
    if not conn:
        return {
            "kpis": {
                "total_trades": 0,
                "initial_balance": DEFAULT_INITIAL_BALANCE,
                "final_balance": DEFAULT_INITIAL_BALANCE,
                "roi": 0.0,
                "benchmark_roi": 0.0,
            },
            "trades": [],
        }

    try:
        df = pd.read_sql("SELECT * FROM positions_log ORDER BY open_timestamp ASC", conn)
    except Exception as exc:
        logger.exception("Failed to read positions_log: %s", exc)
        return {
            "kpis": {
                "total_trades": 0,
                "initial_balance": DEFAULT_INITIAL_BALANCE,
                "final_balance": DEFAULT_INITIAL_BALANCE,
                "roi": 0.0,
                "benchmark_roi": 0.0,
            },
            "trades": [],
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if df.empty:
        return {
            "kpis": {
                "total_trades": 0,
                "initial_balance": DEFAULT_INITIAL_BALANCE,
                "final_balance": DEFAULT_INITIAL_BALANCE,
                "roi": 0.0,
                "benchmark_roi": 0.0,
            },
            "trades": [],
        }

    df = df.copy()
    if "close_timestamp" in df.columns and "open_timestamp" in df.columns:
        df["__sort_ts"] = df["close_timestamp"].where(pd.notna(df["close_timestamp"]), df["open_timestamp"])
        df = df.sort_values(by="__sort_ts", ascending=True)
    elif "close_timestamp" in df.columns:
        df = df.sort_values(by="close_timestamp", ascending=True)
    elif "open_timestamp" in df.columns:
        df = df.sort_values(by="open_timestamp", ascending=True)

    initial_balance = DEFAULT_INITIAL_BALANCE
    if "initial_balance" in df.columns and pd.notna(df.iloc[0].get("initial_balance")):
        initial_balance = _to_float(df.iloc[0].get("initial_balance"), DEFAULT_INITIAL_BALANCE)
    elif "balance_before" in df.columns and pd.notna(df.iloc[0].get("balance_before")):
        initial_balance = _to_float(df.iloc[0].get("balance_before"), DEFAULT_INITIAL_BALANCE)

    pnl_series = df.get("final_profit_usd", pd.Series([0] * len(df))).fillna(0)
    amount_in_series = df.get("capital_allocated_usd", pd.Series([0] * len(df))).fillna(0)

    if "balance_after" in df.columns:
        balance_after_series = df["balance_after"].fillna(method="ffill")
        balance_after_list = [_to_float(value, initial_balance) for value in balance_after_series]
    else:
        running_balance = initial_balance
        balance_after_list = []
        for pnl_value in pnl_series:
            running_balance += _to_float(pnl_value, 0.0)
            balance_after_list.append(running_balance)

    trades: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        amount_in = _to_float(row.get("capital_allocated_usd"))
        pnl = _to_float(row.get("final_profit_usd"))
        amount_out = amount_in + pnl
        balance_after = balance_after_list[idx] if idx < len(balance_after_list) else initial_balance

        close_ts = row.get("close_timestamp")
        open_ts = row.get("open_timestamp")
        date_value = close_ts if pd.notna(close_ts) else open_ts

        trades.append(
            {
                "date": _format_date(date_value),
                "type": _infer_trade_type(row.get("strategy_used")),
                "amount_in": amount_in,
                "amount_out": amount_out,
                "balance_after": balance_after,
                "pnl_percent": (pnl / amount_in * 100) if amount_in else 0.0,
            }
        )

    trades.sort(key=lambda trade: trade.get("date") or "")

    final_balance = balance_after_list[-1] if balance_after_list else initial_balance
    roi = ((final_balance - initial_balance) / initial_balance * 100) if initial_balance else 0.0

    return {
        "kpis": {
            "total_trades": int(len(trades)),
            "initial_balance": float(initial_balance),
            "final_balance": float(final_balance),
            "roi": float(roi),
            "benchmark_roi": 0.0,
        },
        "trades": trades,
    }
