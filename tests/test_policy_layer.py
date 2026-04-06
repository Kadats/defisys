import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from backend.src.core.policy_layer import PolicyLayerStrategy
from backend.src.ai.regime_classifier import MarketRegime
from backend.src.core import TradingEngine

@pytest.fixture
def mock_engine():
    engine = MagicMock(spec=TradingEngine)
    engine.active_lps = []
    engine.btc_hodl_balance = 0.0
    return engine

@patch('backend.src.core.policy_layer.detect_regime')
def test_policy_layer_bull_routes_to_btc_lite(mock_detect_regime, mock_engine):
    mock_detect_regime.return_value = MarketRegime.BULL
    
    policy = PolicyLayerStrategy()
    policy.bull_strategy = MagicMock()
    policy.bull_strategy.execute.return_value = {"action": "BULL_ACTION"}
    
    row = pd.Series({'Close': 50000, 'ATR': 100})
    timestamp = pd.Timestamp('2024-01-01')
    
    result = policy.execute(row, mock_engine, timestamp)
    
    assert result["action"] == "BULL_ACTION"
    policy.bull_strategy.execute.assert_called_once_with(row, mock_engine, timestamp)

@patch('backend.src.core.policy_layer.detect_regime')
def test_policy_layer_bear_routes_to_swing_usd(mock_detect_regime, mock_engine):
    mock_detect_regime.return_value = MarketRegime.BEAR
    
    policy = PolicyLayerStrategy()
    policy.bear_strategy = MagicMock()
    policy.bear_strategy.execute.return_value = {"action": "BEAR_ACTION"}
    
    row = pd.Series({'Close': 30000, 'ATR': 100})
    timestamp = pd.Timestamp('2024-01-01')
    
    result = policy.execute(row, mock_engine, timestamp)
    
    assert result["action"] == "BEAR_ACTION"
    policy.bear_strategy.execute.assert_called_once_with(row, mock_engine, timestamp)

@patch('backend.src.core.policy_layer.detect_regime')
def test_policy_layer_uncertain_forces_abstain(mock_detect_regime, mock_engine):
    mock_detect_regime.return_value = MarketRegime.UNCERTAIN
    
    # Mock some active positions
    mock_engine.active_lps = [{'id': 1}, {'id': 2}]
    mock_engine.btc_hodl_balance = 1.5
    
    policy = PolicyLayerStrategy()
    
    row = pd.Series({'Close': 40000, 'ATR': 100})
    timestamp = pd.Timestamp('2024-01-01')
    
    result = policy.execute(row, mock_engine, timestamp)
    
    assert result["action"] == "ABSTAIN"
    assert result["reason"] == "Regime is UNCERTAIN. Forced 100% Cash."
    
    # Verify LPs were closed
    assert mock_engine.close_lp.call_count == 2
    mock_engine.close_lp.assert_any_call(1, 40000.0, timestamp, is_emergency=True)
    mock_engine.close_lp.assert_any_call(2, 40000.0, timestamp, is_emergency=True)
    
    # Verify Spot BTC was sold
    mock_engine.sell_btc.assert_called_once_with(1.5, 40000.0, timestamp)

@patch('backend.src.core.policy_layer.detect_regime')
def test_policy_layer_sideways_routes_to_sideways(mock_detect_regime, mock_engine):
    mock_detect_regime.return_value = MarketRegime.SIDEWAYS
    
    policy = PolicyLayerStrategy()
    policy.sideways_strategy = MagicMock()
    policy.sideways_strategy.execute.return_value = {"action": "SIDEWAYS_ACTION"}
    
    row = pd.Series({'Close': 40000, 'ATR': 100})
    timestamp = pd.Timestamp('2024-01-01')
    
    result = policy.execute(row, mock_engine, timestamp)
    
    assert result["action"] == "SIDEWAYS_ACTION"
    policy.sideways_strategy.execute.assert_called_once_with(row, mock_engine, timestamp)
