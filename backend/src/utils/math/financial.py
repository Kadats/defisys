"""
Financial calculations for position sizing and risk management.

Pure functions for calculating entry sizes, drawdowns, and risk metrics.
"""


def calculate_drawdown(
    ath_price: float,
    current_price: float
) -> float:
    """
    Calculate the drawdown from all-time high.
    
    Drawdown = (ATH - Current) / ATH
    
    Args:
        ath_price: All-time high price
        current_price: Current market price
    
    Returns:
        Drawdown as a decimal (e.g., 0.30 for 30% drawdown)
        Returns 0.0 if current price >= ATH
    """
    if ath_price <= 0:
        return 0.0
    
    drawdown = (ath_price - current_price) / ath_price
    return max(0.0, drawdown)  # Drawdown cannot be negative


def calculate_entry_size(
    usd_balance: float,
    current_price: float,
    ath_price: float,
    fng_value: float,
    base_allocation: float = 0.20,
    drawdown_threshold: float = 0.30,
    fng_threshold: float = 20.0,
    max_allocation: float = 0.80,
    min_liquid_buffer: float = 0.20
) -> float:
    """
    Calculate dynamic allocation percentage based on market conditions.
    
    V4 Dynamic Allocation: Returns a percentage (0.0 to 1.0) of balance to allocate
    based on drawdown from ATH and Fear & Greed Index sentiment.
    
    Args:
        usd_balance: Available USD balance (not used in calculation, for signature compatibility)
        current_price: Current BTC price
        ath_price: All-time high BTC price
        fng_value: Fear & Greed Index (0-100)
        base_allocation: Base allocation percentage (default 0.20 = 20%)
        drawdown_threshold: Drawdown threshold to trigger aggressive (default 0.30 = 30%)
        fng_threshold: FNG threshold to trigger aggressive (default 20.0 = Extreme Fear)
        max_allocation: Maximum allocation percentage (default 0.80 = 80%)
        min_liquid_buffer: Minimum liquidity buffer to preserve (default 0.20 = 20%)
    
    Returns:
        Allocation percentage (0.0 to 1.0) of balance to allocate
    
    Logic:
        - Start with base_allocation (20%)
        - If drawdown > threshold (30%), increase to 70%
        - If FNG < threshold (20), increase to 70%
        - Cap at max_allocation (80%)
        - Ensure we never breach min_liquid_buffer (20%)
    """
    if ath_price <= 0:
        return base_allocation
    
    # Calculate drawdown from ATH
    drawdown = calculate_drawdown(ath_price, current_price)
    
    # Start with base allocation
    allocation_pct = base_allocation
    
    # Aggressive buying: Deep drawdown (price far below ATH)
    if drawdown > drawdown_threshold:
        allocation_pct = 0.70
    
    # Extreme fear index: Buy more when sentiment is very negative
    if fng_value < fng_threshold:
        allocation_pct = max(allocation_pct, 0.70)
    
    # Cap at maximum allocation
    allocation_pct = min(allocation_pct, max_allocation)
    
    # Ensure we never breach the minimum liquid buffer
    max_allocable = 1.0 - min_liquid_buffer
    allocation_pct = min(allocation_pct, max_allocable)
    
    return allocation_pct


def calculate_position_value(
    btc_amount: float,
    btc_price: float,
    usd_amount: float = 0.0
) -> float:
    """
    Calculate total position value in USD.
    
    Args:
        btc_amount: Amount of BTC held
        btc_price: Current BTC price
        usd_amount: Amount of USD held (default 0.0)
    
    Returns:
        Total value in USD
    """
    return (btc_amount * btc_price) + usd_amount


def calculate_leverage_ratio(
    total_collateral: float,
    total_debt: float
) -> float:
    """
    Calculate the effective leverage ratio of a position.
    
    Leverage = (Collateral + Debt) / Collateral
    
    Args:
        total_collateral: Total collateral value
        total_debt: Total debt amount
    
    Returns:
        Leverage ratio (1.0 = no leverage, 2.0 = 2x, etc.)
    """
    if total_collateral <= 0:
        return 0.0
    
    return (total_collateral + total_debt) / total_collateral


def calculate_profit_loss(
    entry_value: float,
    exit_value: float,
    fees_paid: float = 0.0
) -> float:
    """
    Calculate profit/loss of a position.
    
    Args:
        entry_value: Initial position value
        exit_value: Final position value
        fees_paid: Total fees incurred (default 0.0)
    
    Returns:
        Net P&L in USD (positive = profit, negative = loss)
    """
    return exit_value - entry_value - fees_paid


def calculate_roi(
    entry_value: float,
    exit_value: float,
    fees_paid: float = 0.0
) -> float:
    """
    Calculate return on investment as a percentage.
    
    Args:
        entry_value: Initial position value
        exit_value: Final position value
        fees_paid: Total fees incurred
    
    Returns:
        ROI as decimal (e.g., 0.15 for 15% return)
    """
    if entry_value <= 0:
        return 0.0
    
    pnl = calculate_profit_loss(entry_value, exit_value, fees_paid)
    return pnl / entry_value
