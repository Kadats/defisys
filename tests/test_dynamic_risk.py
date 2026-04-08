import pytest
from backend.src.core.risk_manager import RiskManager

def test_dynamic_risk_manager_drawdown():
    # max_global_drawdown default here won't be used if regime is explicitly handled, 
    # but we set it just in case.
    rm = RiskManager(gas_reserve_usd=50.0, simulated_gas_fee_usd=1.0, max_global_drawdown=0.15)
    
    # 1. Test BULL regime (Limit is 20%)
    # HWM = 1000. Drop 19% -> 810. Should be SAFE.
    status = rm.check_drawdown_limits(current_equity=810.0, global_hwm=1000.0, daily_hwm=0.0, regime='BULL')
    assert status == 'SAFE', "Should be SAFE in BULL regime with 19% drawdown"
    
    # HWM = 1000. Drop 21% -> 790. Should trigger KILL_SWITCH.
    status = rm.check_drawdown_limits(current_equity=790.0, global_hwm=1000.0, daily_hwm=0.0, regime='BULL')
    assert status == 'KILL_SWITCH', "Should be KILL_SWITCH in BULL regime with >20% drawdown"

    # 2. Test BEAR regime (Limit is 10%)
    # HWM = 1000. Drop 9% -> 910. Should be SAFE.
    status = rm.check_drawdown_limits(current_equity=910.0, global_hwm=1000.0, daily_hwm=0.0, regime='BEAR')
    assert status == 'SAFE', "Should be SAFE in BEAR regime with 9% drawdown"

    # HWM = 1000. Drop 11% -> 890. Should trigger KILL_SWITCH.
    status = rm.check_drawdown_limits(current_equity=890.0, global_hwm=1000.0, daily_hwm=0.0, regime='BEAR')
    assert status == 'KILL_SWITCH', "Should be KILL_SWITCH in BEAR regime with >10% drawdown"

    # 3. Test UNCERTAIN regime (Limit is 15%)
    # HWM = 1000. Drop 11% -> 890. Should be SAFE.
    status = rm.check_drawdown_limits(current_equity=890.0, global_hwm=1000.0, daily_hwm=0.0, regime='UNCERTAIN')
    assert status == 'SAFE', "Should be SAFE in UNCERTAIN regime with 11% drawdown"

    # HWM = 1000. Drop 16% -> 840. Should trigger KILL_SWITCH.
    status = rm.check_drawdown_limits(current_equity=840.0, global_hwm=1000.0, daily_hwm=0.0, regime='UNCERTAIN')
    assert status == 'KILL_SWITCH', "Should be KILL_SWITCH in UNCERTAIN regime with >15% drawdown"
