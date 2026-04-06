import pytest
import pandas as pd

from backend.src.ai.ensemble import calculate_confidence_sizing, evaluate_ensemble_signal
from backend.src.ai.regime_classifier import MarketRegime

def test_confidence_sizing_abstain():
    assert calculate_confidence_sizing(0.50) == 0.0
    assert calculate_confidence_sizing(0.69) == 0.0

def test_confidence_sizing_scaled():
    # At 70%, it should be 0.1
    assert calculate_confidence_sizing(0.70) == pytest.approx(0.1)
    
    # At 75%, it's 1/3 of the way between 0.70 and 0.85, so 1/3 between 0.1 and 0.3 -> 0.166...
    assert calculate_confidence_sizing(0.75) == pytest.approx(0.1667, rel=1e-3)
    
    # At 80%, it's 2/3 of the way -> 0.233...
    assert calculate_confidence_sizing(0.80) == pytest.approx(0.2333, rel=1e-3)
    
    # At 85%, it should be 0.3
    assert calculate_confidence_sizing(0.85) == pytest.approx(0.3)

def test_confidence_sizing_full():
    assert calculate_confidence_sizing(0.86) == 1.0
    assert calculate_confidence_sizing(0.99) == 1.0

def test_evaluate_ensemble_signal():
    # UNCERTAIN -> False
    assert evaluate_ensemble_signal(MarketRegime.UNCERTAIN, 0.90, 0.02) is False
    
    # High volatility but low prediction -> False
    assert evaluate_ensemble_signal(MarketRegime.BULL, 0.80, 0.06) is False
    
    # High volatility but high prediction -> True
    assert evaluate_ensemble_signal(MarketRegime.BULL, 0.90, 0.06) is True
    
    # Normal -> True
    assert evaluate_ensemble_signal(MarketRegime.BEAR, 0.75, 0.03) is True
