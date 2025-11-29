"""
Lending protocol mathematical formulas.

Pure functions for calculating health factors, safe borrow amounts,
and compound interest for DeFi lending protocols.
"""


def calculate_health_factor(
    collateral_value: float,
    debt: float,
    liquidation_threshold: float = 0.8
) -> float:
    """
    Calculate the health factor for a leveraged position.
    
    Health Factor = (Collateral Value * Liquidation Threshold) / Debt
    
    Args:
        collateral_value: Total value of collateral in USD
        debt: Total debt amount in USD
        liquidation_threshold: LTV threshold for liquidation (default 0.8 = 80%)
    
    Returns:
        Health factor (HF > 1.0 is safe, HF < 1.0 triggers liquidation)
    """
    if debt <= 0:
        return float('inf')  # No debt means infinite health
    
    return (collateral_value * liquidation_threshold) / debt


def calculate_safe_borrow_amount(
    collateral_value: float,
    current_debt: float = 0.0,
    target_hf: float = 2.0,
    liquidation_threshold: float = 0.8,
    min_borrow: float = 10.0
) -> float:
    """
    Calculate the maximum safe amount to borrow while maintaining a target health factor.
    
    This function computes how much can be borrowed given existing collateral and debt
    while keeping the health factor at or above the target level.
    
    Args:
        collateral_value: Total value of collateral in USD
        current_debt: Existing debt amount in USD (default 0.0)
        target_hf: Desired health factor (default 2.0)
        liquidation_threshold: LTV threshold (default 0.8 = 80%)
        min_borrow: Minimum borrow amount to execute (default $10)
    
    Returns:
        Maximum safe borrow amount in USD. Returns 0 if:
        - Collateral insufficient
        - Current HF already below target
        - Calculated amount below minimum
    """
    # No collateral means no borrowing
    if collateral_value <= 0:
        return 0.0
    
    # Check current health factor if there's existing debt
    if current_debt > 0:
        current_hf = calculate_health_factor(
            collateral_value, current_debt, liquidation_threshold
        )
        # Don't allow more borrowing if already below target HF
        if current_hf < target_hf:
            return 0.0
    
    # Calculate max total debt allowed for target HF
    # From HF = (Collateral * LT) / Debt, we solve for Debt:
    # Debt = (Collateral * LT) / target_HF
    max_total_debt = (collateral_value * liquidation_threshold) / target_hf
    
    # Additional borrow capacity is max total debt minus current debt
    additional_borrow = max_total_debt - current_debt
    
    # Don't borrow if below minimum threshold
    if additional_borrow < min_borrow:
        return 0.0
    
    return additional_borrow


def calculate_compound_interest(
    principal: float,
    rate: float,
    periods: int
) -> float:
    """
    Calculate compound interest over discrete periods.
    
    Formula: A = P * (1 + r)^n
    
    Args:
        principal: Initial principal amount
        rate: Interest rate per period (e.g., 0.075 for 7.5%)
        periods: Number of compounding periods
    
    Returns:
        Total amount after compounding (principal + interest)
    """
    if principal <= 0 or periods <= 0:
        return principal
    
    return principal * ((1 + rate) ** periods)


def calculate_interest_accrued(
    principal: float,
    rate: float,
    periods: int
) -> float:
    """
    Calculate only the interest portion (not including principal).
    
    Args:
        principal: Initial principal amount
        rate: Interest rate per period
        periods: Number of compounding periods
    
    Returns:
        Interest accrued (total amount - principal)
    """
    total = calculate_compound_interest(principal, rate, periods)
    return total - principal
