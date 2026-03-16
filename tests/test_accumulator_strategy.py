import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from backend.src.strategies.accumulator import AccumulatorStrategy

@pytest.fixture
def strategy():
    return AccumulatorStrategy(use_llm=False)

@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.usd_balance = 1000.0
    engine.btc_hodl_balance = 0.0
    engine.btc_collateral_balance = 0.0
    engine.total_debt_usd = 0.0
    engine.health_factor = 999.0
    engine.active_lps = []
    return engine

@pytest.fixture
def sample_row():
    return pd.Series({
        'Close': 60000.0,
        'prediction': 1,
        'prediction_proba': 0.8,
        'RSI': 40.0
    })

def test_is_cooldown_passed(strategy):
    now = pd.Timestamp('2025-01-01 12:00:00')
    # No previous trade
    assert strategy._is_cooldown_passed(now) is True
    
    # Just traded
    strategy.last_trade_time = now
    assert strategy._is_cooldown_passed(now) is False
    
    # 13 hours later (COOLDOWN_HOURS = 12)
    later = now + pd.Timedelta(hours=13)
    assert strategy._is_cooldown_passed(later) is True

def test_analyze_market_entry(strategy):
    timestamp = pd.Timestamp('2025-01-01')
    
    # Momentum Entry: proba > 0.65, RSI < 75
    res = strategy._analyze_market_entry(0.8, 40.0, timestamp)
    assert res['type'] == 'MOMENTUM'
    
    # Dip Entry: proba > 0.55, RSI < 60
    res = strategy._analyze_market_entry(0.6, 50.0, timestamp)
    assert res['type'] == 'DIP'
    
    # Overbought Momentum
    res = strategy._analyze_market_entry(0.8, 80.0, timestamp)
    assert res is None
    
    # Low confidence
    res = strategy._analyze_market_entry(0.4, 40.0, timestamp)
    assert res is None

@patch('backend.src.strategies.accumulator.consult_risk_agent')
def test_execute_defense_mode_trigger(mock_agent, strategy, mock_engine, sample_row):
    mock_engine.health_factor = 1.2 # Critical
    mock_engine.active_lps = [{'id': 1}]
    
    strategy.execute(sample_row, mock_engine, pd.Timestamp('2025-01-01'))
    
    # Should close LP in defense mode
    mock_engine.close_lp.assert_called()

@patch('backend.src.strategies.accumulator.consult_risk_agent')
def test_execute_routes_to_bull_entry(mock_agent, strategy, mock_engine, sample_row):
    # Mock agent to recommend BORROW_AND_LP
    mock_agent.return_value = {
        'action': 'BORROW_AND_LP',
        'amount_pct': 0.5,
        'reason': 'test bull'
    }
    strategy.use_llm = True
    
    # Ensure engine has enough balance and btc_hodl_balance becomes > 0
    mock_engine.usd_balance = 1000.0
    
    # We need to simulate that buy_and_hodl increases btc_hodl_balance 
    # so that add_collateral is triggered.
    def mock_buy(amt, price, ts=None):
        mock_engine.btc_hodl_balance += amt / price
        mock_engine.usd_balance -= amt
        
    mock_engine.buy_and_hodl.side_effect = mock_buy
    
    # We also need to simulate add_collateral moving BTC to collateral balance
    def mock_collateral(amt):
        mock_engine.btc_collateral_balance += amt
        mock_engine.btc_hodl_balance -= amt
        
    mock_engine.add_collateral.side_effect = mock_collateral
    
    # Simulate borrow_funds adding to usd_balance
    def mock_borrow(amt, price):
        mock_engine.usd_balance += amt
        return amt
        
    mock_engine.borrow_funds.side_effect = mock_borrow
    
    strategy.execute(sample_row, mock_engine, pd.Timestamp('2025-01-01'))
    
    # Should buy spot first in bull entry
    mock_engine.buy_and_hodl.assert_called()
    # Should add collateral (because btc_hodl_balance > 0 now)
    mock_engine.add_collateral.assert_called()
    # Should borrow (HF is 999.0 > 2.0)
    mock_engine.borrow_funds.assert_called()
    # Should open LP
    mock_engine.open_lp.assert_called()

@patch('backend.src.strategies.accumulator.consult_risk_agent')
def test_execute_routes_to_spot_only(mock_agent, strategy, mock_engine, sample_row):
    mock_agent.return_value = {
        'action': 'SPOT_ONLY',
        'amount_pct': 0.2,
        'reason': 'test spot'
    }
    strategy.use_llm = True
    
    strategy.execute(sample_row, mock_engine, pd.Timestamp('2025-01-01'))
    
    mock_engine.buy_and_hodl.assert_called()
    mock_engine.open_lp.assert_not_called()
