"""
Uniswap V3 mathematical formulas.

Pure functions for calculating liquidity positions, amounts, and values
in Uniswap V3 concentrated liquidity pools.

CRITICAL: All calculations use decimal.Decimal for maximum precision
to avoid floating-point errors in financial calculations.
"""
from decimal import Decimal, getcontext
from typing import Tuple, Union

# Set precision to 28 decimal places for DeFi calculations
getcontext().prec = 28


def _to_decimal(value: Union[int, float, str, Decimal]) -> Decimal:
    """
    Convert input value to Decimal safely.
    
    Args:
        value: Input value (int, float, str, or Decimal)
    
    Returns:
        Decimal representation of the value
    """
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _sqrt(value: Decimal) -> Decimal:
    """
    Calculate square root using Decimal precision.
    
    Args:
        value: Decimal value to calculate square root of
    
    Returns:
        Square root as Decimal
    """
    return value.sqrt()


def calculate_lp_value(
    liquidity: Union[int, float, str, Decimal],
    range_lower: Union[int, float, str, Decimal],
    range_upper: Union[int, float, str, Decimal],
    current_price: Union[int, float, str, Decimal]
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculate the value and composition of a Uniswap V3 LP position.
    
    Args:
        liquidity: The liquidity value (L) of the position
        range_lower: Lower price bound (pa)
        range_upper: Upper price bound (pb)
        current_price: Current market price (pc)
    
    Returns:
        Tuple of (total_value_usd, amount_btc, amount_usdt) as Decimal
    """
    L = _to_decimal(liquidity)
    pa = _to_decimal(range_lower)
    pb = _to_decimal(range_upper)
    pc = _to_decimal(current_price)
    
    sqrt_pa = _sqrt(pa)
    sqrt_pb = _sqrt(pb)
    sqrt_pc = _sqrt(pc)
    
    amount_btc = Decimal('0')
    amount_usdt = Decimal('0')
    
    if pc <= pa:
        # Price below range - all position in BTC
        amount_btc = L * ((Decimal('1') / sqrt_pa) - (Decimal('1') / sqrt_pb))
    elif pc >= pb:
        # Price above range - all position in USD
        amount_usdt = L * (sqrt_pb - sqrt_pa)
    else:
        # Price in range - mixed position
        amount_btc = L * ((Decimal('1') / sqrt_pc) - (Decimal('1') / sqrt_pb))
        amount_usdt = L * (sqrt_pc - sqrt_pa)
    
    total_value = (amount_btc * pc) + amount_usdt
    return total_value, amount_btc, amount_usdt


def calculate_liquidity_l(
    capital_usd: Union[int, float, str, Decimal],
    range_lower: Union[int, float, str, Decimal],
    range_upper: Union[int, float, str, Decimal],
    current_price: Union[int, float, str, Decimal]
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculate liquidity L and initial amounts for a new LP position.
    
    Args:
        capital_usd: Total capital to deploy in USD
        range_lower: Lower price bound (pa)
        range_upper: Upper price bound (pb)
        current_price: Current market price (pc)
    
    Returns:
        Tuple of (liquidity_L, amount_btc, amount_usdt) as Decimal
    """
    capital = _to_decimal(capital_usd)
    pa = _to_decimal(range_lower)
    pb = _to_decimal(range_upper)
    pc = _to_decimal(current_price)
    
    sqrt_pa = _sqrt(pa)
    sqrt_pb = _sqrt(pb)
    sqrt_pc = _sqrt(pc)
    
    amount_btc = Decimal('0')
    amount_usdt = Decimal('0')
    L = Decimal('0')
    
    # Check for division by zero
    if (sqrt_pb - sqrt_pa) == Decimal('0'):
        return Decimal('0'), Decimal('0'), Decimal('0')
    
    if pc <= pa:
        # Price below range - all capital becomes BTC
        L = ((capital / pc) * sqrt_pa * sqrt_pb) / (sqrt_pb - sqrt_pa)
        amount_btc = capital / pc
    elif pc >= pb:
        # Price above range - all capital stays USD
        L = capital / (sqrt_pb - sqrt_pa)
        amount_usdt = capital
    else:
        # Price in range - mixed allocation
        denominator = (Decimal('2') * sqrt_pc - sqrt_pa - (pc / sqrt_pb))
        if denominator == Decimal('0'):
            return Decimal('0'), Decimal('0'), Decimal('0')
        L = capital / denominator
        amount_usdt = L * (sqrt_pc - sqrt_pa)
        amount_btc = L * ((Decimal('1') / sqrt_pc) - (Decimal('1') / sqrt_pb))
    
    return L, amount_btc, amount_usdt


def calculate_amounts_from_liquidity(
    liquidity: Union[int, float, str, Decimal],
    range_lower: Union[int, float, str, Decimal],
    range_upper: Union[int, float, str, Decimal],
    current_price: Union[int, float, str, Decimal]
) -> Tuple[Decimal, Decimal]:
    """
    Calculate BTC and USD amounts from a given liquidity value.
    
    Args:
        liquidity: The liquidity value (L)
        range_lower: Lower price bound (pa)
        range_upper: Upper price bound (pb)
        current_price: Current market price (pc)
    
    Returns:
        Tuple of (amount_btc, amount_usdt) as Decimal
    """
    _, amount_btc, amount_usdt = calculate_lp_value(
        liquidity, range_lower, range_upper, current_price
    )
    return amount_btc, amount_usdt


def estimate_fees(
    lp_value_usd: Union[int, float, str, Decimal],
    pool_tvl_usd: Union[int, float, str, Decimal],
    pool_volume_24h_usd: Union[int, float, str, Decimal],
    pool_fee_rate: Union[int, float, str, Decimal] = Decimal('0.003')
) -> Decimal:
    """
    Estimate fees earned by an LP position based on pool metrics.
    
    Args:
        lp_value_usd: Value of the LP position in USD
        pool_tvl_usd: Total Value Locked in the pool
        pool_volume_24h_usd: 24-hour trading volume
        pool_fee_rate: Pool fee rate (default 0.3%)
    
    Returns:
        Estimated fees earned in USD as Decimal
    """
    lp_val = _to_decimal(lp_value_usd)
    pool_tvl = _to_decimal(pool_tvl_usd)
    pool_volume = _to_decimal(pool_volume_24h_usd)
    fee_rate = _to_decimal(pool_fee_rate) if not isinstance(pool_fee_rate, Decimal) else pool_fee_rate
    
    if pool_tvl <= Decimal('0') or pool_volume <= Decimal('0'):
        return Decimal('0')
    
    # Calculate LP's share of the pool
    pool_share = lp_val / pool_tvl
    
    # Calculate total fees generated
    total_fees = pool_volume * fee_rate
    
    # Return LP's proportional share of fees
    return total_fees * pool_share
