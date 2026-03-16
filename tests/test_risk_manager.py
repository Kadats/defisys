import pytest
from backend.src.core.risk_manager import RiskManager

@pytest.fixture
def risk_manager():
    return RiskManager(
        gas_reserve_usd=50.0,
        simulated_gas_fee_usd=1.0,
        hf_warning=1.3,
        hf_critical=1.1,
        hf_refinance=2.0,
        liquidation_threshold=0.8
    )

def test_risk_manager_calculate_health_factor(risk_manager):
    # (1000 * 0.8) / 500 = 1.6
    assert risk_manager.calculate_health_factor(1000.0, 500.0) == 1.6
    # No debt
    assert risk_manager.calculate_health_factor(1000.0, 0.0) == 999.0

def test_risk_manager_check_health_status(risk_manager):
    # SAFE: (1000 * 0.8) / 500 = 1.6 > 1.3
    status, hf = risk_manager.check_health_status(1000.0, 500.0)
    assert status == 'SAFE'
    assert hf == 1.6
    
    # WARNING: (1000 * 0.8) / 650 = 1.23 < 1.3
    status, hf = risk_manager.check_health_status(1000.0, 650.0)
    assert status == 'WARNING'
    
    # CRITICAL: (1000 * 0.8) / 750 = 1.06 < 1.1
    status, hf = risk_manager.check_health_status(1000.0, 750.0)
    assert status == 'CRITICAL'
    
    # LIQUIDATION: (1000 * 0.8) / 850 = 0.94 < 1.0
    status, hf = risk_manager.check_health_status(1000.0, 850.0)
    assert status == 'LIQUIDATION'

def test_risk_manager_can_afford_gas(risk_manager):
    assert risk_manager.can_afford_gas(10.0) is True
    assert risk_manager.can_afford_gas(0.5) is False

def test_risk_manager_should_emergency_close(risk_manager):
    # gas_reserve=50, multiplier=0.5 -> threshold=25
    assert risk_manager.should_emergency_close(20.0) is True # Below 25, can afford 1.0
    assert risk_manager.should_emergency_close(0.5) is False # Below 25, but CANNOT afford 1.0
    assert risk_manager.should_emergency_close(30.0) is False # Above 25

def test_risk_manager_can_refinance(risk_manager):
    assert risk_manager.can_refinance(2.5) is True
    assert risk_manager.can_refinance(1.5) is False

def test_risk_manager_calculate_safe_balance(risk_manager):
    assert risk_manager.calculate_safe_balance(100.0) == 50.0
    assert risk_manager.calculate_safe_balance(30.0) == 0.0

def test_risk_manager_assess_rebalance_options(risk_manager):
    # Case: SAFE (HF >= 1.3)
    res = risk_manager.assess_rebalance_options(1.6, 100.0, True)
    assert res['action'] == 'none'
    
    # Case: Emergency close (HF < 1.3 AND low gas)
    # hf_warning is 1.3. For HF 1.2 and balance 20.0 (< 25.0) -> emergency_close
    res = risk_manager.assess_rebalance_options(1.2, 20.0, True)
    assert res['action'] == 'emergency_close'
    
    # Case: Pay debt with cash (HF < 1.3 AND balance > 50.0)
    # The current implementation requires HF < hf_warning (1.3) to even consider paying debt
    res = risk_manager.assess_rebalance_options(1.2, 100.0, True)
    assert res['action'] == 'pay_debt_with_cash'
    assert res['available_cash'] == 50.0
    
    # Case: Close LP (HF < 1.3 AND no cash)
    res = risk_manager.assess_rebalance_options(1.2, 50.0, True)
    assert res['action'] == 'close_lp'
