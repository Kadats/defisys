import pytest
from backend.src.utils.math.lending import (
    calculate_health_factor,
    calculate_safe_borrow_amount,
    calculate_compound_interest,
    calculate_interest_accrued
)

def test_calculate_health_factor():
    # Collateral 1000, debt 500, threshold 0.8 -> (1000 * 0.8) / 500 = 800 / 500 = 1.6
    assert calculate_health_factor(1000.0, 500.0, 0.8) == 1.6
    # No debt -> infinite health
    assert calculate_health_factor(1000.0, 0.0) == float('inf')
    # Liquidation case: (1000 * 0.8) / 900 = 0.888...
    assert calculate_health_factor(1000.0, 900.0) == pytest.approx(0.8888, rel=1e-3)

def test_calculate_safe_borrow_amount():
    # Collateral 1000, target HF 2.0, threshold 0.8
    # max_total_debt = (1000 * 0.8) / 2.0 = 400
    # current_debt 0 -> safe_borrow 400
    assert calculate_safe_borrow_amount(1000.0, 0.0, 2.0, 0.8) == 400.0
    
    # current_debt 100 -> safe_borrow 300
    assert calculate_safe_borrow_amount(1000.0, 100.0, 2.0, 0.8) == 300.0
    
    # Already below target HF: HF = (1000 * 0.8) / 500 = 1.6 < 2.0
    assert calculate_safe_borrow_amount(1000.0, 500.0, 2.0, 0.8) == 0.0
    
    # Calculated borrow below minimum ($10)
    # max_total_debt 400, current_debt 395 -> additional 5 < 10
    assert calculate_safe_borrow_amount(1000.0, 395.0, 2.0, 0.8, min_borrow=10.0) == 0.0
    
    # No collateral
    assert calculate_safe_borrow_amount(0.0, 0.0) == 0.0

def test_calculate_compound_interest():
    # 1000 at 10% for 2 periods -> 1000 * 1.1 * 1.1 = 1210
    assert calculate_compound_interest(1000.0, 0.1, 2) == pytest.approx(1210.0)
    # Principal 0
    assert calculate_compound_interest(0.0, 0.1, 5) == 0.0
    # Periods 0
    assert calculate_compound_interest(1000.0, 0.1, 0) == 1000.0

def test_calculate_interest_accrued():
    # 1000 at 10% for 2 periods -> 210 interest
    assert calculate_interest_accrued(1000.0, 0.1, 2) == pytest.approx(210.0)
