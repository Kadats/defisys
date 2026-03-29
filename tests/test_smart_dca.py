import pytest
import pandas as pd
from unittest.mock import MagicMock
from backend.src.strategies.smart_dca import SmartDCAStrategy

@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.usd_balance = 1000.0
    engine.btc_hodl_balance = 0.0
    engine.gas_fee_usd = 0.10
    engine.slippage_pct = 0.001
    return engine

def test_smart_dca_first_entry(mock_engine):
    strategy = SmartDCAStrategy()
    # High confidence (0.55 >= 0.55)
    row = pd.Series({'Close': 50000.0, 'prediction_proba': 0.55})
    timestamp = pd.Timestamp('2026-03-27')
    
    strategy.execute(row, mock_engine, timestamp)
    
    # Must allocate 25% of 1000 = 250
    mock_engine.buy_and_hodl.assert_called_once()
    args, _ = mock_engine.buy_and_hodl.call_args
    assert args[0] == 250.0 # amount_usd
    assert strategy.orders_placed == 1
    assert strategy.average_entry_price == 50000.0

def test_smart_dca_entry_skipped_low_proba(mock_engine):
    strategy = SmartDCAStrategy()
    # Low confidence (0.54 < 0.55)
    row = pd.Series({'Close': 50000.0, 'prediction_proba': 0.54})
    timestamp = pd.Timestamp('2026-03-27')
    
    strategy.execute(row, mock_engine, timestamp)
    
    mock_engine.buy_and_hodl.assert_not_called()
    assert strategy.orders_placed == 0

def test_smart_dca_second_bullet(mock_engine):
    strategy = SmartDCAStrategy()
    strategy.orders_placed = 1
    strategy.average_entry_price = 50000.0
    mock_engine.btc_hodl_balance = 0.005 # $250 @ 50000
    mock_engine.usd_balance = 750.0
    
    # Price dropped -6% (47000 <= 50000 * 0.95 = 47500)
    # ML Confidence >= 0.52 (0.53)
    row = pd.Series({'Close': 47000.0, 'prediction_proba': 0.53})
    timestamp = pd.Timestamp('2026-03-27')
    
    # We need a way for the strategy to know the initial capital to calc the bullet size
    # Let's assume the bullet size is 25% of current usd_balance + current btc_value if 1st bullet
    # Or simpler: if 1st bullet, bullet = 25% of engine.usd_balance.
    # Subsequent bullets = use the same bullet size as the first one.
    # Let's say strategy stores the bullet_size.
    strategy.bullet_size = 250.0 
    
    strategy.execute(row, mock_engine, timestamp)
    
    mock_engine.buy_and_hodl.assert_called_once_with(250.0, 47000.0, timestamp)
    assert strategy.orders_placed == 2
    # New average: (50000 * 0.005 + 47000 * (250/47000)) / (0.005 + 250/47000)
    # 0.005 BTC @ 50000 = $250
    # ~0.005319 BTC @ 47000 = $250
    # Total $500 / Total ~0.010319 BTC = ~48454
    assert 48000 < strategy.average_entry_price < 49000

def test_smart_dca_take_profit(mock_engine):
    strategy = SmartDCAStrategy()
    strategy.orders_placed = 2
    strategy.average_entry_price = 48454.0
    mock_engine.btc_hodl_balance = 0.010319
    
    # Price is +6% above average (51000 > 48454 * 1.05 = 50876.7)
    row = pd.Series({'Close': 51000.0, 'prediction_proba': 0.50})
    timestamp = pd.Timestamp('2026-03-27')
    
    strategy.execute(row, mock_engine, timestamp)
    
    mock_engine.sell_btc.assert_called_once_with(0.010319, 51000.0, timestamp)
    assert strategy.orders_placed == 0
    assert strategy.average_entry_price == 0.0

def test_smart_dca_stop_loss_hard(mock_engine):
    strategy = SmartDCAStrategy()
    strategy.orders_placed = 1
    strategy.average_entry_price = 50000.0
    mock_engine.btc_hodl_balance = 0.005
    
    # Price dropped -16% (42000 < 50000 * 0.85 = 42500)
    row = pd.Series({'Close': 42000.0, 'prediction_proba': 0.50})
    timestamp = pd.Timestamp('2026-03-27')
    
    strategy.execute(row, mock_engine, timestamp)
    
    mock_engine.sell_btc.assert_called_once_with(0.005, 42000.0, timestamp)
    assert strategy.orders_placed == 0
    assert strategy.average_entry_price == 0.0

def test_smart_dca_abort_trend(mock_engine):
    strategy = SmartDCAStrategy()
    strategy.orders_placed = 1
    strategy.average_entry_price = 50000.0
    mock_engine.btc_hodl_balance = 0.005
    
    # ML Confidence < 0.40 (0.39)
    row = pd.Series({'Close': 50000.0, 'prediction_proba': 0.39})
    timestamp = pd.Timestamp('2026-03-27')
    
    strategy.execute(row, mock_engine, timestamp)
    
    mock_engine.sell_btc.assert_called_once_with(0.005, 50000.0, timestamp)
    assert strategy.orders_placed == 0
    assert strategy.average_entry_price == 0.0
