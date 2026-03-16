import pytest
from decimal import Decimal
from backend.src.utils.math.uniswap import (
    calculate_lp_value,
    calculate_liquidity_l,
    calculate_amounts_from_liquidity,
    estimate_fees
)

def test_calculate_lp_value_below_range():
    # Price 50, Range [100, 200], Liquidity 1000
    # Position should be 100% BTC
    val, btc, usd = calculate_lp_value(1000, 100, 200, 50)
    assert usd == 0
    # L * (1/sqrt(pa) - 1/sqrt(pb)) = 1000 * (1/10 - 1/sqrt(200))
    expected_btc = Decimal('1000') * (Decimal('1') / Decimal('100').sqrt() - Decimal('1') / Decimal('200').sqrt())
    assert btc == expected_btc
    assert val == btc * Decimal('50')

def test_calculate_lp_value_above_range():
    # Price 250, Range [100, 200], Liquidity 1000
    # Position should be 100% USD
    val, btc, usd = calculate_lp_value(1000, 100, 200, 250)
    assert btc == 0
    # L * (sqrt(pb) - sqrt(pa)) = 1000 * (sqrt(200) - 10)
    expected_usd = Decimal('1000') * (Decimal('200').sqrt() - Decimal('10'))
    assert usd == expected_usd
    assert val == usd

def test_calculate_lp_value_in_range():
    # Price 144, Range [100, 200], Liquidity 1000
    # mixed position
    val, btc, usd = calculate_lp_value(1000, 100, 200, 144)
    # usd = L * (sqrt(pc) - sqrt(pa)) = 1000 * (12 - 10) = 2000
    assert usd == Decimal('2000')
    # btc = L * (1/sqrt(pc) - 1/sqrt(pb)) = 1000 * (1/12 - 1/sqrt(200))
    expected_btc = Decimal('1000') * (Decimal('1') / Decimal('12') - Decimal('1') / Decimal('200').sqrt())
    assert btc == expected_btc
    assert val == (btc * Decimal('144')) + usd

def test_calculate_liquidity_l_below_range():
    # Capital 1000 USD, Price 50, Range [100, 200]
    # L = (capital/pc * sqrt(pa) * sqrt(pb)) / (sqrt(pb) - sqrt(pa))
    l, btc, usd = calculate_liquidity_l(1000, 100, 200, 50)
    assert usd == 0
    assert btc == Decimal('20') # 1000 / 50
    # L = 20 * 10 * sqrt(200) / (sqrt(200) - 10)
    expected_l = (Decimal('20') * Decimal('10') * Decimal('200').sqrt()) / (Decimal('200').sqrt() - Decimal('10'))
    assert l == pytest.approx(expected_l)

def test_calculate_liquidity_l_above_range():
    # Capital 1000 USD, Price 250, Range [100, 200]
    # L = capital / (sqrt(pb) - sqrt(pa))
    l, btc, usd = calculate_liquidity_l(1000, 100, 200, 250)
    assert btc == 0
    assert usd == 1000
    expected_l = Decimal('1000') / (Decimal('200').sqrt() - Decimal('10'))
    assert l == pytest.approx(expected_l)

def test_calculate_amounts_from_liquidity():
    btc, usd = calculate_amounts_from_liquidity(1000, 100, 200, 144)
    assert usd == Decimal('2000')
    expected_btc = Decimal('1000') * (Decimal('1') / Decimal('12') - Decimal('1') / Decimal('200').sqrt())
    assert btc == expected_btc

def test_estimate_fees():
    # LP 1000, TVL 100000 (1%), Volume 10000, Fee 0.3% (30) -> fees 0.3
    res = estimate_fees(1000, 100000, 10000, 0.003)
    assert res == Decimal('0.3')
    
    # TVL 0
    assert estimate_fees(1000, 0, 10000) == 0
    # Volume 0
    assert estimate_fees(1000, 100000, 0) == 0
