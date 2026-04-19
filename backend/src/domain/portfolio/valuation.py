"""Pure portfolio valuation helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def calculate_portfolio_value(
    *,
    btc_hodl_balance: float,
    btc_collateral_balance: float,
    current_btc_price: float,
    usd_balance: float,
    active_lps: Iterable[dict[str, Any]],
    active_shorts: Iterable[dict[str, Any]],
    yield_total_balance: float,
    total_debt_usd: float,
    get_lp_value_fn,
) -> float:
    """Calculate current portfolio value using the engine positions state."""
    lp_val = 0.0
    for lp in active_lps:
        lp_value_usd, _, _ = get_lp_value_fn(lp, current_btc_price)
        lp_val += (
            float(lp_value_usd)
            + float(lp.get("fees_accrued_usdt", 0.0))
            + (float(lp.get("fees_accrued_btc", 0.0)) * current_btc_price)
        )

    short_val = 0.0
    for short_pos in active_shorts:
        short_val += float(short_pos["collateral_usd"]) + (
            float(short_pos["entry_price"]) - current_btc_price
        ) * float(short_pos["btc_amount"])

    return (
        (btc_hodl_balance + btc_collateral_balance) * current_btc_price
        + usd_balance
        + lp_val
        + short_val
        + yield_total_balance
        - total_debt_usd
    )
