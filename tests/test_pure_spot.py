import pytest
import pandas as pd
from unittest.mock import MagicMock
from backend.src.strategies.pure_spot import PureSpotStrategy

@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.usd_balance = 1000.0
    engine.btc_hodl_balance = 0.0
    engine.gas_fee_usd = 0.10
    engine.slippage_pct = 0.001
    return engine

def test_pure_spot_buy_signal(mock_engine):
    strategy = PureSpotStrategy()
    # Mock data row: High confidence (0.55 >= 0.54)
    row = pd.Series({'Close': 50000.0, 'prediction_proba': 0.55})
    timestamp = pd.Timestamp('2026-03-27')
    
    strategy.execute(row, mock_engine, timestamp)
    
    # Must allocate 90% of 1000 = 900
    mock_engine.buy_and_hodl.assert_called_once()
    args, kwargs = mock_engine.buy_and_hodl.call_args
    assert args[0] == 900.0 # amount_usd
    assert strategy.average_entry_price == 50000.0

def test_pure_spot_take_profit(mock_engine):
    strategy = PureSpotStrategy()
    strategy.average_entry_price = 50000.0
    mock_engine.btc_hodl_balance = 0.018 # Holding some BTC
    
    # Price is +6% (53000 > 50000 * 1.05)
    row = pd.Series({'Close': 53000.0, 'prediction_proba': 0.50})
    timestamp = pd.Timestamp('2026-03-27')
    
    strategy.execute(row, mock_engine, timestamp)
    
    mock_engine.sell_btc.assert_called_once_with(0.018, 53000.0, timestamp)
    assert strategy.average_entry_price == 0.0

def test_pure_spot_stop_loss(mock_engine):
    strategy = PureSpotStrategy()
    strategy.average_entry_price = 50000.0
    mock_engine.btc_hodl_balance = 0.018
    
    # Price is -6% (47000 < 50000 * 0.95)
    row = pd.Series({'Close': 47000.0, 'prediction_proba': 0.50})
    timestamp = pd.Timestamp('2026-03-27')
    
    strategy.execute(row, mock_engine, timestamp)
    
    mock_engine.sell_btc.assert_called_once_with(0.018, 47000.0, timestamp)
    assert strategy.average_entry_price == 0.0

def test_pure_spot_abort_trend(mock_engine):
    strategy = PureSpotStrategy()
    strategy.average_entry_price = 50000.0
    mock_engine.btc_hodl_balance = 0.018
    
    # ML Confidence drops below 0.48
    row = pd.Series({'Close': 50000.0, 'prediction_proba': 0.45})
    timestamp = pd.Timestamp('2026-03-27')
    
    strategy.execute(row, mock_engine, timestamp)
    
    mock_engine.sell_btc.assert_called_once_with(0.018, 50000.0, timestamp)
    assert strategy.average_entry_price == 0.0
