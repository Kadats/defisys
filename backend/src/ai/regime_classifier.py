import pandas as pd
from enum import Enum

class MarketRegime(Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    UNCERTAIN = "UNCERTAIN"

def detect_regime(row: pd.Series) -> MarketRegime:
    """
    Detects the market regime based on available indicators and ML predictions.
    
    Rules (Simplified for V1 Regime Classifier):
    - Missing crucial data -> UNCERTAIN
    - Conflicting strong signals -> UNCERTAIN
    - Price > SMA200 AND ML > 0.6 -> BULL
    - Price < SMA200 AND ML < 0.4 -> BEAR
    - Price ~ SMA200 AND ML ~ 0.5 -> SIDEWAYS
    """
    # 1. Extract values safely
    try:
        close = float(row.get('Close', 0))
        sma_200 = float(row.get('SMA_200', 0))
        rsi = float(row.get('RSI', 50))
        prediction_proba = float(row.get('prediction_proba', 0.5))
        fgi = float(row.get('Fear_Greed_Index', 50))
        atr = float(row.get('ATR', 0))
    except Exception:
        return MarketRegime.UNCERTAIN

    # 2. Check for missing crucial data (if sma_200 is 0, we can't establish trend)
    if sma_200 == 0 or close == 0:
        return MarketRegime.UNCERTAIN

    # 2.5 Check for extreme volatility combined with extreme sentiment (UNCERTAIN)
    # ATR is absolute, we calculate it as a percentage of close price
    atr_pct = atr / close if close > 0 else 0
    is_high_volatility = atr_pct > 0.05
    
    if is_high_volatility and (fgi < 25 or fgi > 75):
        return MarketRegime.UNCERTAIN

    # 3. Calculate trend indicators
    trend_pct = (close - sma_200) / sma_200
    is_above_sma = trend_pct > 0.02
    is_below_sma = trend_pct < -0.02
    is_flat_sma = abs(trend_pct) <= 0.02

    # 4. Check for conflicting signals
    if is_below_sma and rsi < 40 and prediction_proba > 0.8:
        return MarketRegime.UNCERTAIN
    if is_above_sma and rsi > 70 and prediction_proba < 0.2:
        return MarketRegime.UNCERTAIN

    # 5. Classify Regime
    if is_above_sma and prediction_proba > 0.55:
        return MarketRegime.BULL
        
    if is_below_sma and prediction_proba < 0.45:
        return MarketRegime.BEAR
        
    if is_flat_sma and (0.45 <= prediction_proba <= 0.55):
        return MarketRegime.SIDEWAYS

    # Fallback to sideways if it's somewhat stable, else uncertain
    if 40 <= rsi <= 60:
        return MarketRegime.SIDEWAYS
        
    return MarketRegime.UNCERTAIN
