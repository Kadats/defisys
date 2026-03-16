import pytest
from backend.src.utils.math.financial import (
    calculate_drawdown,
    calculate_entry_size,
    calculate_directional_range,
    calculate_dynamic_range,
    calculate_position_value,
    calculate_leverage_ratio,
    calculate_profit_loss,
    calculate_roi
)

def test_calculate_drawdown():
    # ATH is 100, current is 70 -> 30% drawdown
    assert calculate_drawdown(100.0, 70.0) == pytest.approx(0.30)
    # ATH is 100, current is 100 -> 0% drawdown
    assert calculate_drawdown(100.0, 100.0) == 0.0
    # ATH is 100, current is 110 -> 0% drawdown (capped at 0)
    assert calculate_drawdown(100.0, 110.0) == 0.0
    # ATH is 0 or negative
    assert calculate_drawdown(0.0, 50.0) == 0.0
    assert calculate_drawdown(-10.0, 50.0) == 0.0

def test_calculate_entry_size():
    # Base case: no drawdown, neutral FNG
    # base_allocation=0.20, drawdown_threshold=0.30, fng_threshold=20.0
    assert calculate_entry_size(1000.0, 80.0, 100.0, 50.0) == 0.20
    
    # Deep drawdown: 40% (threshold 30%)
    assert calculate_entry_size(1000.0, 60.0, 100.0, 50.0) == 0.70
    
    # Extreme fear: FNG 15 (threshold 20)
    assert calculate_entry_size(1000.0, 90.0, 100.0, 15.0) == 0.70
    
    # Both drawdown and fear
    assert calculate_entry_size(1000.0, 60.0, 100.0, 15.0) == 0.70
    
    # Max allocation cap (0.80)
    # If we change thresholds or logic, we might reach 0.80. 
    # Current logic caps at 0.70 but max_allocation is 0.80 by default.
    # Let's test with custom thresholds to hit caps.
    assert calculate_entry_size(1000.0, 60.0, 100.0, 15.0, max_allocation=0.60) == 0.60
    
    # Min liquid buffer cap (min_liquid_buffer=0.20 -> max 0.80)
    assert calculate_entry_size(1000.0, 60.0, 100.0, 15.0, min_liquid_buffer=0.40) == 0.60

def test_calculate_directional_range():
    # Normal case: current 60000, ATR 2000, multiplier 10
    # lower = 60000 * 0.98 = 58800
    # upper = 60000 + (2000 * 10) = 80000
    lower, upper = calculate_directional_range(60000.0, 2000.0, 10.0)
    assert lower == 58800.0
    assert upper == 80000.0
    
    # ATR is 0: upper = 60000 * 1.30 = 78000
    lower, upper = calculate_directional_range(60000.0, 0.0, 10.0)
    assert lower == 58800.0
    assert upper == 78000.0
    
    # Invalid current price
    lower, upper = calculate_directional_range(0.0, 2000.0)
    assert lower == 0.0
    assert upper == 0.0

def test_calculate_dynamic_range():
    # Normal case: current 60000, ATR 2000, mult_lower 10, mult_upper 20
    # lower = 60000 - (2000 * 10) = 40000
    # upper = 60000 + (2000 * 20) = 100000
    lower, upper = calculate_dynamic_range(60000.0, 2000.0, 10.0, 20.0)
    assert lower == 40000.0
    assert upper == 100000.0
    
    # Sanity check: min_lower = current * 0.5 = 30000
    # If ATR * mult_lower = 40000 -> 60000 - 40000 = 20000
    # lower should be 30000
    lower, upper = calculate_dynamic_range(60000.0, 4000.0, 10.0, 20.0)
    assert lower == 30000.0
    
    # Sanity check: min_upper = current * 1.05 = 63000
    # upper = 60000 + (2000 * 1) = 62000
    # upper should be 63000
    lower, upper = calculate_dynamic_range(60000.0, 2000.0, 10.0, 1.0)
    assert upper == 63000.0
    
    # Invalid ATR or price
    lower, upper = calculate_dynamic_range(60000.0, 0.0, 10.0, 20.0)
    assert lower == 60000.0 * 0.70
    assert upper == 60000.0 * 1.60

def test_calculate_position_value():
    assert calculate_position_value(0.1, 60000.0, 1000.0) == 7000.0
    assert calculate_position_value(0.0, 60000.0, 500.0) == 500.0

def test_calculate_leverage_ratio():
    # Collateral 1000, debt 500 -> (1000+500)/1000 = 1.5
    assert calculate_leverage_ratio(1000.0, 500.0) == 1.5
    assert calculate_leverage_ratio(1000.0, 0.0) == 1.0
    assert calculate_leverage_ratio(0.0, 500.0) == 0.0

def test_calculate_profit_loss():
    assert calculate_profit_loss(1000.0, 1200.0, 10.0) == 190.0
    assert calculate_profit_loss(1000.0, 900.0, 5.0) == -105.0

def test_calculate_roi():
    # P&L = 200 - 10 = 190. ROI = 190/1000 = 0.19
    assert calculate_roi(1000.0, 1200.0, 10.0) == 0.19
    assert calculate_roi(0.0, 1200.0) == 0.0
