import pytest
import pandas as pd
from backend.src.ai.regime_classifier import MarketRegime, detect_regime

def test_detect_regime_bull():
    row = pd.Series({
        'Close': 50000,
        'SMA_200': 40000,
        'RSI': 60,
        'Fear_Greed_Index': 70,
        'prediction_proba': 0.8
    })
    assert detect_regime(row) == MarketRegime.BULL

def test_detect_regime_bear():
    row = pd.Series({
        'Close': 30000,
        'SMA_200': 40000,
        'RSI': 30,
        'Fear_Greed_Index': 20,
        'prediction_proba': 0.2
    })
    assert detect_regime(row) == MarketRegime.BEAR

def test_detect_regime_sideways():
    row = pd.Series({
        'Close': 40000,
        'SMA_200': 40000,
        'RSI': 50,
        'Fear_Greed_Index': 50,
        'prediction_proba': 0.5
    })
    assert detect_regime(row) == MarketRegime.SIDEWAYS

def test_detect_regime_uncertain_conflicting_signals():
    # High ML, but price way below SMA and RSI low
    row = pd.Series({
        'Close': 30000,
        'SMA_200': 50000,
        'RSI': 20,
        'Fear_Greed_Index': 10,
        'prediction_proba': 0.9  # Conflicting strong signal
    })
    assert detect_regime(row) == MarketRegime.UNCERTAIN

def test_detect_regime_uncertain_no_data():
    # Missing crucial data
    row = pd.Series({
        'Close': 40000,
        'RSI': 50,
    })
    assert detect_regime(row) == MarketRegime.UNCERTAIN
