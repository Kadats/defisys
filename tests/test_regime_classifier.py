import pytest
import pandas as pd
from backend.src.ai.regime_classifier import MarketRegime, detect_regime

def test_detect_regime_bull():
    row = pd.Series({
        'Close': 50000,
        'SMA_200': 40000,
        'RSI': 60,
        'Fear_Greed_Index': 70,
        'ATR': 1000, # 2% volatility
        'prediction_proba': 0.8
    })
    assert detect_regime(row) == MarketRegime.BULL

def test_detect_regime_bear():
    row = pd.Series({
        'Close': 30000,
        'SMA_200': 40000,
        'RSI': 30,
        'Fear_Greed_Index': 20,
        'ATR': 1000, # 3.3% volatility
        'prediction_proba': 0.2
    })
    assert detect_regime(row) == MarketRegime.BEAR

def test_detect_regime_sideways():
    row = pd.Series({
        'Close': 40000,
        'SMA_200': 40000,
        'RSI': 50,
        'Fear_Greed_Index': 50,
        'ATR': 500, # 1.25% volatility
        'prediction_proba': 0.5
    })
    assert detect_regime(row) == MarketRegime.SIDEWAYS

def test_detect_regime_uncertain_conflicting_signals():
    row = pd.Series({
        'Close': 30000,
        'SMA_200': 50000,
        'RSI': 20,
        'Fear_Greed_Index': 10,
        'ATR': 1000,
        'prediction_proba': 0.9  # Conflicting strong signal
    })
    assert detect_regime(row) == MarketRegime.UNCERTAIN

def test_detect_regime_uncertain_no_data():
    row = pd.Series({
        'Close': 40000,
        'RSI': 50,
    })
    assert detect_regime(row) == MarketRegime.UNCERTAIN

def test_detect_regime_uncertain_extreme_fear_volatility():
    # ATR is 10% of close, and FGI is very low -> panic, should abstain
    row = pd.Series({
        'Close': 40000,
        'SMA_200': 41000,
        'RSI': 30,
        'Fear_Greed_Index': 15,
        'ATR': 4000, # 10% volatility
        'prediction_proba': 0.4
    })
    assert detect_regime(row) == MarketRegime.UNCERTAIN

def test_detect_regime_uncertain_extreme_greed_volatility():
    # ATR is 8% of close, and FGI is very high -> irrational exuberance / blow-off top
    row = pd.Series({
        'Close': 60000,
        'SMA_200': 40000,
        'RSI': 85,
        'Fear_Greed_Index': 90,
        'ATR': 4800, # 8% volatility
        'prediction_proba': 0.9
    })
    assert detect_regime(row) == MarketRegime.UNCERTAIN

def test_detect_regime_rapid_fgi_drop():
    # Rapid drop in Fear & Greed Index (> 20 points)
    row = pd.Series({
        'Close': 40000,
        'SMA_200': 35000,
        'RSI': 50,
        'Fear_Greed_Index': 40,
        'FGI_Drop_24h': 25,
        'ATR': 1000,
        'prediction_proba': 0.4
    })
    assert detect_regime(row) == MarketRegime.UNCERTAIN
