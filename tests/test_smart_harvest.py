import pytest
import pandas as pd
import math
from backend.src.backtester import Backtester, POOL_FEE_RATE, LIQUIDATION_THRESHOLD
from backend.src.config import SIMULATED_GAS_FEE_USD


@pytest.fixture
def fresh_backtester():
    """Retorna uma instância nova do Backtester com $1000."""
    return Backtester(initial_capital_usd=1000.0)


@pytest.fixture
def lp_with_fees(fresh_backtester):
    """Creates a backtester with an LP that has accumulated fees."""
    bt = fresh_backtester
    bt.open_lp(1000.0, 100.0, 400.0, 225.0, pd.Timestamp('2025-01-01'))
    lp = bt.active_lps[0]
    return bt, lp


def test_harvest_only_if_fees_exceed_threshold(lp_with_fees):
    """Test that harvest respects the minimum fee threshold (10 * GAS_FEE)."""
    bt, lp = lp_with_fees
    initial_usd = bt.usd_balance
    
    # Set fees below threshold
    threshold = SIMULATED_GAS_FEE_USD * 10
    lp['fees_accrued_usdt'] = threshold - 0.5  # Just below threshold
    lp['fees_accrued_btc'] = 0.0
    
    # Call harvest
    bt._check_and_harvest(current_price=225.0, timestamp=pd.Timestamp('2025-01-02'))
    
    # Fees should NOT be harvested (no change in balance)
    assert bt.usd_balance == initial_usd
    assert lp['fees_accrued_usdt'] == threshold - 0.5
    assert len(bt.decision_history) == 1  # Only OPEN LP decision


def test_harvest_when_fees_exceed_threshold(lp_with_fees):
    """Test that harvest occurs when fees exceed the minimum threshold."""
    bt, lp = lp_with_fees
    initial_usd = bt.usd_balance
    initial_collateral = bt.btc_hodl_balance
    
    # Set fees above threshold
    threshold = SIMULATED_GAS_FEE_USD * 10
    usdt_fees = threshold + 5.0
    btc_fees = 0.01
    
    lp['fees_accrued_usdt'] = usdt_fees
    lp['fees_accrued_btc'] = btc_fees
    
    # Call harvest
    bt._check_and_harvest(current_price=225.0, timestamp=pd.Timestamp('2025-01-02'))
    
    # Gas fee should be deducted
    expected_usd = initial_usd + usdt_fees - SIMULATED_GAS_FEE_USD
    assert bt.usd_balance == pytest.approx(expected_usd, rel=1e-6)
    
    # BTC fees should go to collateral
    expected_collateral = initial_collateral + btc_fees
    assert bt.btc_hodl_balance == pytest.approx(expected_collateral, rel=1e-6)
    
    # Fees should be reset
    assert lp['fees_accrued_usdt'] == 0.0
    assert lp['fees_accrued_btc'] == 0.0
    
    # Should have harvest log
    assert any("HARVEST" in decision for decision in bt.decision_history)


def test_harvest_gas_fee_deducted(lp_with_fees):
    """Test that gas fee is correctly deducted from USD balance."""
    bt, lp = lp_with_fees
    initial_usd = bt.usd_balance
    
    threshold = SIMULATED_GAS_FEE_USD * 10
    lp['fees_accrued_usdt'] = threshold + 10.0
    lp['fees_accrued_btc'] = 0.0
    
    # Call harvest
    bt._check_and_harvest(current_price=225.0, timestamp=pd.Timestamp('2025-01-02'))
    
    # Verify gas was deducted (USD fees added minus gas deducted)
    expected_usd = initial_usd + threshold + 10.0 - SIMULATED_GAS_FEE_USD
    assert bt.usd_balance == pytest.approx(expected_usd, rel=1e-6)


def test_harvest_btc_fees_to_collateral(lp_with_fees):
    """Test that BTC fees are routed to collateral (auto-compound)."""
    bt, lp = lp_with_fees
    initial_collateral = bt.btc_hodl_balance
    
    threshold = SIMULATED_GAS_FEE_USD * 10
    btc_fees = 0.05
    
    lp['fees_accrued_usdt'] = threshold + 5.0
    lp['fees_accrued_btc'] = btc_fees
    
    # Call harvest
    bt._check_and_harvest(current_price=225.0, timestamp=pd.Timestamp('2025-01-02'))
    
    # BTC fees should increase collateral
    expected_collateral = initial_collateral + btc_fees
    assert bt.btc_hodl_balance == pytest.approx(expected_collateral, rel=1e-6)


def test_harvest_usd_fees_to_balance(lp_with_fees):
    """Test that USD fees are routed to USD balance (cash reserve)."""
    bt, lp = lp_with_fees
    initial_usd = bt.usd_balance
    
    threshold = SIMULATED_GAS_FEE_USD * 10
    usdt_fees = threshold + 20.0
    
    lp['fees_accrued_usdt'] = usdt_fees
    lp['fees_accrued_btc'] = 0.0
    
    # Call harvest
    bt._check_and_harvest(current_price=225.0, timestamp=pd.Timestamp('2025-01-02'))
    
    # USD fees should increase balance (minus gas)
    expected_usd = initial_usd + usdt_fees - SIMULATED_GAS_FEE_USD
    assert bt.usd_balance == pytest.approx(expected_usd, rel=1e-6)


def test_harvest_logs_to_decision_history(lp_with_fees):
    """Test that harvest decision is logged in decision_history."""
    bt, lp = lp_with_fees
    lp_id = lp['id']
    
    threshold = SIMULATED_GAS_FEE_USD * 10
    usdt_fees = threshold + 5.0
    btc_fees = 0.02
    
    lp['fees_accrued_usdt'] = usdt_fees
    lp['fees_accrued_btc'] = btc_fees
    
    # Call harvest
    timestamp = pd.Timestamp('2025-01-02')
    bt._check_and_harvest(current_price=225.0, timestamp=timestamp)
    
    # Check for harvest log
    harvest_logs = [d for d in bt.decision_history if "HARVEST" in d]
    assert len(harvest_logs) == 1
    assert f"LP {lp_id}" in harvest_logs[0]
    assert "BTC to Collateral" in harvest_logs[0]
    assert "USD" in harvest_logs[0]
    assert "Gas" in harvest_logs[0]


def test_harvest_insufficient_gas_balance(lp_with_fees):
    """Test that harvest skips if insufficient USD balance to pay gas."""
    bt, lp = lp_with_fees
    
    # Reduce USD balance below gas fee
    bt.usd_balance = SIMULATED_GAS_FEE_USD - 0.10
    initial_usd = bt.usd_balance
    
    threshold = SIMULATED_GAS_FEE_USD * 10
    lp['fees_accrued_usdt'] = threshold + 5.0
    lp['fees_accrued_btc'] = 0.01
    
    # Call harvest
    bt._check_and_harvest(current_price=225.0, timestamp=pd.Timestamp('2025-01-02'))
    
    # Should not harvest due to insufficient balance
    assert bt.usd_balance == initial_usd
    assert lp['fees_accrued_usdt'] == threshold + 5.0  # Fees unchanged
    assert lp['fees_accrued_btc'] == 0.01  # Fees unchanged


def test_harvest_multiple_lps(fresh_backtester):
    """Test that harvest works correctly with multiple LPs."""
    bt = fresh_backtester
    
    # Open two LPs
    bt.open_lp(500.0, 100.0, 300.0, 200.0, pd.Timestamp('2025-01-01'))
    bt.open_lp(500.0, 200.0, 400.0, 300.0, pd.Timestamp('2025-01-02'))
    
    lp1, lp2 = bt.active_lps[0], bt.active_lps[1]
    
    # Set fees on first LP above threshold
    threshold = SIMULATED_GAS_FEE_USD * 10
    lp1['fees_accrued_usdt'] = threshold + 5.0
    lp1['fees_accrued_btc'] = 0.01
    
    # Set fees on second LP below threshold
    lp2['fees_accrued_usdt'] = threshold - 1.0
    lp2['fees_accrued_btc'] = 0.0
    
    initial_usd = bt.usd_balance
    initial_collateral = bt.btc_hodl_balance
    
    # Call harvest
    bt._check_and_harvest(current_price=250.0, timestamp=pd.Timestamp('2025-01-03'))
    
    # Only LP1 should be harvested
    assert lp1['fees_accrued_usdt'] == 0.0
    assert lp1['fees_accrued_btc'] == 0.0
    
    # LP2 should not be harvested
    assert lp2['fees_accrued_usdt'] == threshold - 1.0
    
    # Balance should reflect LP1 harvest only
    expected_usd = initial_usd + threshold + 5.0 - SIMULATED_GAS_FEE_USD
    assert bt.usd_balance == pytest.approx(expected_usd, rel=1e-6)
    
    # Collateral should increase from LP1 BTC fees only
    expected_collateral = initial_collateral + 0.01
    assert bt.btc_hodl_balance == pytest.approx(expected_collateral, rel=1e-6)


def test_harvest_no_lps(fresh_backtester):
    """Test that harvest does nothing if there are no active LPs."""
    bt = fresh_backtester
    initial_usd = bt.usd_balance
    
    # Call harvest with no LPs
    bt._check_and_harvest(current_price=225.0, timestamp=pd.Timestamp('2025-01-02'))
    
    # Nothing should change
    assert bt.usd_balance == initial_usd
    assert len(bt.active_lps) == 0


def test_harvest_zero_btc_fees(lp_with_fees):
    """Test harvest with only USD fees (no BTC fees)."""
    bt, lp = lp_with_fees
    initial_collateral = bt.btc_hodl_balance
    
    threshold = SIMULATED_GAS_FEE_USD * 10
    lp['fees_accrued_usdt'] = threshold + 10.0
    lp['fees_accrued_btc'] = 0.0
    
    # Call harvest
    bt._check_and_harvest(current_price=225.0, timestamp=pd.Timestamp('2025-01-02'))
    
    # Collateral should not change
    assert bt.btc_hodl_balance == initial_collateral
    
    # USD should increase by fees minus gas
    expected_usd_increase = threshold + 10.0 - SIMULATED_GAS_FEE_USD
    assert lp['fees_accrued_usdt'] == 0.0


def test_harvest_zero_usd_fees(lp_with_fees):
    """Test harvest with only BTC fees (no USD fees)."""
    bt, lp = lp_with_fees
    initial_usd = bt.usd_balance
    initial_collateral = bt.btc_hodl_balance
    
    threshold = SIMULATED_GAS_FEE_USD * 10
    btc_fees = 0.03
    
    # Set USD fees to exactly trigger threshold with the BTC value
    # total_fees_usd = usdt_fees + btc_fees * price = threshold + 5
    # So: usdt_fees = threshold + 5 - (0.03 * 225) = 5 + 5 - 6.75 = 3.25
    lp['fees_accrued_usdt'] = 3.25
    lp['fees_accrued_btc'] = btc_fees
    
    # Call harvest
    bt._check_and_harvest(current_price=225.0, timestamp=pd.Timestamp('2025-01-02'))
    
    # BTC should go to collateral
    assert bt.btc_hodl_balance == pytest.approx(initial_collateral + btc_fees, rel=1e-6)
    
    # USD should be: initial + usdt_fees - gas_fee = initial + 3.25 - 0.50
    expected_usd = initial_usd + 3.25 - SIMULATED_GAS_FEE_USD
    assert bt.usd_balance == pytest.approx(expected_usd, rel=1e-6)

