"""
Ensemble Voting System and Position Sizing.
"""

def evaluate_ensemble_signal(regime, prediction_proba: float, atr_pct: float) -> bool:
    """
    Evaluates a signal based on Regime, Direction (prediction_proba), and Volatility (ATR).
    If it's UNCERTAIN, or volatility is extremely high without a very high prediction_proba,
    returns False.
    """
    from backend.src.ai.regime_classifier import MarketRegime
    if regime == MarketRegime.UNCERTAIN:
        return False
        
    if atr_pct > 0.05 and prediction_proba < 0.85:
        return False
        
    return True

def calculate_confidence_sizing(prediction_proba: float) -> float:
    """
    Calculates the 'ultra-distrustful' position sizing multiplier.
    
    Confidence curve:
    - < 0.70: 0.0 (Abstention)
    - 0.70 to 0.85: Scaled from 0.1 to 0.3 (10% to 30%)
    - > 0.85: 1.0 (Full sizing allowed by the strategy/risk manager)
    """
    if pd.isna(prediction_proba):
        return 0.0
        
    if prediction_proba < 0.70:
        return 0.0
        
    if prediction_proba > 0.85:
        return 1.0
        
    # Scale between 0.70 and 0.85 -> Map to 0.1 to 0.3
    # slope = (0.3 - 0.1) / (0.85 - 0.70) = 0.2 / 0.15 = 1.333...
    slope = 0.2 / 0.15
    sizing = 0.1 + (prediction_proba - 0.70) * slope
    return float(round(sizing, 4))

import pandas as pd
