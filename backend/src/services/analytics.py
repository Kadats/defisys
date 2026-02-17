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
        # Ler da tabela trades ao invés de positions_log
        df = pd.read_sql("SELECT * FROM trades ORDER BY timestamp ASC", conn)
    except Exception as exc:
        logger.exception("Failed to read trades: %s", exc)
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

    # Converter transaction_log para formato esperado pelo frontend
    trades: List[Dict[str, Any]] = []
    balance = DEFAULT_INITIAL_BALANCE
    btc_accumulated = 0.0  # Track accumulated BTC for total equity calculation
    btc_price_final = 0.0  # Track final BTC price
    
    for idx, row in df.iterrows():
        action = row.get("action", "")
        usd_amount = _to_float(row.get("usd_amount", 0))
        btc_amount = _to_float(row.get("btc_amount", 0))
        pnl_usd = _to_float(row.get("pnl_usd", 0))
        fee_usd = _to_float(row.get("fee_usd", 0))
        btc_price = _to_float(row.get("btc_price", 0))
        
        # CRITICAL FIX: Track final BTC price and accumulated BTC for equity calculation
        if btc_price > 0:
            btc_price_final = btc_price
        
        # Atualizar o saldo baseado na ação
        if action == "BUY_HODL":
            balance -= (usd_amount + fee_usd)
            amount_in = usd_amount + fee_usd
            amount_out = 0
            trade_type = "Buy"
            pnl_percent = 0.0
            # Track accumulated BTC
            if btc_amount > 0:
                btc_accumulated += btc_amount
        elif action == "OPEN_LP":
            balance -= (usd_amount + fee_usd)
            amount_in = usd_amount + fee_usd
            amount_out = 0
            trade_type = "Open LP"
            pnl_percent = 0.0
        elif action == "CLOSE_LP":
            balance += (pnl_usd - fee_usd)
            amount_in = usd_amount  # capital original
            amount_out = usd_amount + pnl_usd
            trade_type = "Close LP"
            pnl_percent = (pnl_usd / usd_amount * 100) if usd_amount > 0 else 0.0
        elif action == "HARVEST":
            balance += pnl_usd - fee_usd
            amount_in = 0
            amount_out = pnl_usd
            trade_type = "Harvest"
            pnl_percent = 100.0 if pnl_usd > 0 else 0.0
        elif action == "BORROW":
            balance += usd_amount
            amount_in = 0
            amount_out = usd_amount
            trade_type = "Borrow"
            pnl_percent = 0.0
        elif action == "DEBT_REPAY":
            balance -= usd_amount
            amount_in = usd_amount
            amount_out = 0
            trade_type = "Repay"
            pnl_percent = 0.0
        else:
            # Outras ações (EMERGENCY_CLOSE, etc.)
            balance += (pnl_usd - fee_usd)
            amount_in = usd_amount
            amount_out = usd_amount + pnl_usd
            trade_type = action
            pnl_percent = (pnl_usd / usd_amount * 100) if usd_amount > 0 else 0.0
        
        # Formatar data
        date_str = _format_date(row.get("timestamp"))
        
        trades.append({
            "date": date_str,
            "type": trade_type,
            "amount_in": amount_in,
            "amount_out": amount_out,
            "balance_after": balance,
            "pnl_percent": pnl_percent,
        })

    # CRITICAL FIX: Calculate total equity = cash balance + BTC value
    btc_value = btc_accumulated * btc_price_final
    final_balance = balance + btc_value
    
    # Log the calculation for debugging
    if btc_accumulated > 0:
        logger.info(
            f"📊 Total Equity Calculation: Cash ${balance:.2f} + "
            f"BTC {btc_accumulated:.6f} @ ${btc_price_final:.2f} = ${final_balance:.2f}"
        )
    
    roi = ((final_balance - DEFAULT_INITIAL_BALANCE) / DEFAULT_INITIAL_BALANCE * 100) if DEFAULT_INITIAL_BALANCE > 0 else 0.0

    return {
        "kpis": {
            "total_trades": int(len(trades)),
            "initial_balance": float(DEFAULT_INITIAL_BALANCE),
            "final_balance": float(final_balance),
            "roi": float(roi),
            "benchmark_roi": 0.0,
        },
        "trades": trades,
    }
