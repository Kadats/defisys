"""
Math utilities for DeFi calculations.

This package contains pure mathematical functions for:
- Uniswap V3 liquidity calculations
- Lending protocol calculations
- Financial metrics and allocation strategies
"""

from .uniswap import (
    calculate_lp_value,
    calculate_liquidity_l,
    calculate_amounts_from_liquidity,
)

from .lending import (
    calculate_health_factor,
    calculate_safe_borrow_amount,
    calculate_compound_interest,
)

from .financial import (
    calculate_entry_size,
    calculate_drawdown,
)

__all__ = [
    # Uniswap
    'calculate_lp_value',
    'calculate_liquidity_l',
    'calculate_amounts_from_liquidity',
    # Lending
    'calculate_health_factor',
    'calculate_safe_borrow_amount',
    'calculate_compound_interest',
    # Financial
    'calculate_entry_size',
    'calculate_drawdown',
]
