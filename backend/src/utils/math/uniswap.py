"""
Uniswap V3 mathematical formulas.

Pure functions for calculating liquidity positions, amounts, and values
in Uniswap V3 concentrated liquidity pools.
"""
import math
from typing import Tuple


def calculate_lp_value(
    liquidity: float,
    range_lower: float,
    range_upper: float,
    current_price: float
) -> Tuple[float, float, float]:
    """
    Calculate the value and composition of a Uniswap V3 LP position.
    
    Args:
        liquidity: The liquidity value (L) of the position
        range_lower: Lower price bound (pa)
        range_upper: Upper price bound (pb)
        current_price: Current market price (pc)
    
    Returns:
        Tuple of (total_value_usd, amount_btc, amount_usdt)
    """
    L = liquidity
    pa = range_lower
    pb = range_upper
    pc = current_price
    
    sqrt_pa = math.sqrt(pa)
    sqrt_pb = math.sqrt(pb)
    sqrt_pc = math.sqrt(pc)
    
    amount_btc = 0.0
    amount_usdt = 0.0
    
    if pc <= pa:
        # Price below range - all position in BTC
        amount_btc = L * ((1/sqrt_pa) - (1/sqrt_pb))
    elif pc >= pb:
        # Price above range - all position in USD
        amount_usdt = L * (sqrt_pb - sqrt_pa)
    else:
        # Price in range - mixed position
        amount_btc = L * ((1/sqrt_pc) - (1/sqrt_pb))
        amount_usdt = L * (sqrt_pc - sqrt_pa)
    
    total_value = (amount_btc * pc) + amount_usdt
    return total_value, amount_btc, amount_usdt


def calculate_liquidity_l(
    capital_usd: float,
    range_lower: float,
    range_upper: float,
    current_price: float
) -> Tuple[float, float, float]:
    """
    Calculate liquidity L and initial amounts for a new LP position.
    
    Args:
        capital_usd: Total capital to deploy in USD
        range_lower: Lower price bound (pa)
        range_upper: Upper price bound (pb)
        current_price: Current market price (pc)
    
    Returns:
        Tuple of (liquidity_L, amount_btc, amount_usdt)
    """
    pa = range_lower
    pb = range_upper
    pc = current_price
    
    sqrt_pa = math.sqrt(pa)
    sqrt_pb = math.sqrt(pb)
    sqrt_pc = math.sqrt(pc)
    
    amount_btc = 0.0
    amount_usdt = 0.0
    L = 0.0
    
    # Check for division by zero
    if (sqrt_pb - sqrt_pa) == 0:
        return 0.0, 0.0, 0.0
    
    if pc <= pa:
        # Price below range - all capital becomes BTC
        L = ((capital_usd / pc) * sqrt_pa * sqrt_pb) / (sqrt_pb - sqrt_pa)
        amount_btc = capital_usd / pc
    elif pc >= pb:
        # Price above range - all capital stays USD
        L = capital_usd / (sqrt_pb - sqrt_pa)
        amount_usdt = capital_usd
    else:
        # Price in range - mixed allocation
        denominator = (2 * sqrt_pc - sqrt_pa - (pc / sqrt_pb))
        if denominator == 0:
            return 0.0, 0.0, 0.0
        L = capital_usd / denominator
        amount_usdt = L * (sqrt_pc - sqrt_pa)
        amount_btc = L * ((1/sqrt_pc) - (1/sqrt_pb))
    
    return L, amount_btc, amount_usdt


def calculate_amounts_from_liquidity(
    liquidity: float,
    range_lower: float,
    range_upper: float,
    current_price: float
) -> Tuple[float, float]:
    """
    Calculate BTC and USD amounts from a given liquidity value.
    
    Args:
        liquidity: The liquidity value (L)
        range_lower: Lower price bound (pa)
        range_upper: Upper price bound (pb)
        current_price: Current market price (pc)
    
    Returns:
        Tuple of (amount_btc, amount_usdt)
    """
    _, amount_btc, amount_usdt = calculate_lp_value(
        liquidity, range_lower, range_upper, current_price
    )
    return amount_btc, amount_usdt


def estimate_fees(
    lp_value_usd: float,
    pool_tvl_usd: float,
    pool_volume_24h_usd: float,
    pool_fee_rate: float = 0.003
) -> float:
    """
    Estimate fees earned by an LP position based on pool metrics.
    
    Args:
        lp_value_usd: Value of the LP position in USD
        pool_tvl_usd: Total Value Locked in the pool
        pool_volume_24h_usd: 24-hour trading volume
        pool_fee_rate: Pool fee rate (default 0.3%)
    
    Returns:
        Estimated fees earned in USD
    """
    if pool_tvl_usd <= 0 or pool_volume_24h_usd <= 0:
        return 0.0
    
    # Calculate LP's share of the pool
    pool_share = lp_value_usd / pool_tvl_usd
    
    # Calculate total fees generated
    total_fees = pool_volume_24h_usd * pool_fee_rate
    
    # Return LP's proportional share of fees
    return total_fees * pool_share
