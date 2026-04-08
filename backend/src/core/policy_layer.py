import pandas as pd
from typing import TYPE_CHECKING
import logging

from backend.src.strategies.base import BaseStrategy
from backend.src.strategies.btc_lite import BTCLiteStrategy
from backend.src.strategies.swing_usd import SwingUSDStrategy
from backend.src.ai.regime_classifier import MarketRegime, detect_regime
from backend.src.ai.ensemble import evaluate_ensemble_signal, calculate_confidence_sizing

if TYPE_CHECKING:
    from backend.src.core.trading_engine import TradingEngine

logger = logging.getLogger(__name__)

class PolicyLayerStrategy(BaseStrategy):
    """
    Policy Layer that dynamically routes execution to specialized strategies
    based on the current market regime detected by the RegimeClassifier.
    """
    
    def __init__(self, use_llm: bool = False):
        self.bull_strategy = BTCLiteStrategy()
        # Dual Path for BEAR Market (Fase 5)
        self.bear_strategy_yield = SwingUSDStrategy(use_llm=use_llm, mode="YIELD_PRESERVATION")
        # self.bear_strategy_short = AggressiveShortStrategy() # Placeholder para Fase 5.2
        
        self.sideways_strategy = SwingUSDStrategy(use_llm=use_llm) # SwingUSD can handle mean reversion/sideways
        self.current_regime = MarketRegime.UNCERTAIN

    def execute(self, row: pd.Series, engine: 'TradingEngine', timestamp: pd.Timestamp) -> dict:
        """
        Detects regime and routes to the appropriate strategy.
        Forces abstention (100% USD Cash) if the regime is UNCERTAIN.
        """
        # --- KILL SWITCH CHECK ---
        if getattr(engine, 'is_killed', False):
            return {
                "action": "ABSTAIN",
                "sizing": 0.0,
                "reason": "[KILL SWITCH] System is killed. Refusing all orders.",
                "expected_risk": "Low"
            }
            
        # 1. Detect the current market regime
        self.current_regime = detect_regime(row)
        current_price = float(row.get('Close', 0.0))
        prediction_proba = float(row.get('prediction_proba', 0.5))
        atr = float(row.get('ATR', 0.0))
        atr_pct = atr / current_price if current_price > 0 else 0.0
        
        # 2. Ensemble Veto Check
        is_signal_valid = evaluate_ensemble_signal(self.current_regime, prediction_proba, atr_pct)
        if not is_signal_valid:
            # Veto applied: Force Abstention
            self._force_100_percent_cash(engine, current_price, timestamp)
            return {
                "action": "ABSTAIN",
                "sizing": 0.0,
                "reason": f"Ensemble vetoed signal. Regime={self.current_regime.name}, ML={prediction_proba:.2f}, ATR_pct={atr_pct:.3f}. Forced Cash.",
                "expected_risk": "Low"
            }
            
        # 3. Route to Strategy
        decision = {}
        if self.current_regime == MarketRegime.BULL:
            decision = self.bull_strategy.execute(row, engine, timestamp)
            
        elif self.current_regime == MarketRegime.BEAR:
            # Dual Path Architecture for Bear Market
            bear_path = "YIELD_PRESERVATION" # Path A
            
            if bear_path == "YIELD_PRESERVATION":
                decision = self.bear_strategy_yield.execute(row, engine, timestamp)
            elif bear_path == "AGGRESSIVE_SHORT":
                decision = {
                    "action": "HOLD",
                    "sizing": 0.0,
                    "reason": "Aggressive Short not implemented",
                    "expected_risk": "High"
                }
            
        elif self.current_regime == MarketRegime.SIDEWAYS:
            decision = self.sideways_strategy.execute(row, engine, timestamp)
            
        elif self.current_regime == MarketRegime.UNCERTAIN:
            # Force Abstention: Move to 100% USD Cash
            self._force_100_percent_cash(engine, current_price, timestamp)
            
            return {
                "action": "ABSTAIN",
                "sizing": 0.0,
                "reason": "Regime is UNCERTAIN. Forced 100% Cash.",
                "expected_risk": "Low"
            }
        else:
            decision = {
                "action": "HOLD",
                "sizing": 0.0,
                "reason": "Unknown regime fallback.",
                "expected_risk": "Med"
            }
            
        # 4. "Ultra-Distrustful" Position Sizer
        # Only scale directional entries, don't scale exits or holds
        if decision.get("action") in ["DIRECTIONAL_ENTRY", "BUY", "OPEN_LP"]:
            confidence_multiplier = calculate_confidence_sizing(prediction_proba)
            original_sizing = decision.get("sizing", 0.0)
            new_sizing = original_sizing * confidence_multiplier
            
            if new_sizing == 0.0:
                logger.info(f"[{timestamp.date()}] 🛡️ Ensemble Position Sizer reduced sizing to 0 (Abstention). ML={prediction_proba:.2%}")
                decision["action"] = "ABSTAIN"
                decision["sizing"] = 0.0
                decision["reason"] += f" [Ensemble Veto: low ML {prediction_proba:.2f}]"
            else:
                logger.info(f"[{timestamp.date()}] ⚖️ Ensemble Position Sizer adjusted sizing from {original_sizing:.2f} to {new_sizing:.2f} (Multiplier: {confidence_multiplier:.2f})")
                decision["sizing"] = new_sizing
                decision["reason"] += f" [Ensemble Multiplier: {confidence_multiplier:.2f}]"
                
        return decision

    def _force_100_percent_cash(self, engine: 'TradingEngine', current_price: float, timestamp: pd.Timestamp):
        """
        Closes all active positions (LPs) and sells all spot BTC
        to return the portfolio entirely to USD cash.
        """
        # 1. Close all LPs
        if hasattr(engine, 'active_lps'):
            lp_ids_to_close = [lp['id'] for lp in engine.active_lps]
            for lp_id in lp_ids_to_close:
                engine.close_lp(lp_id, current_price, timestamp, is_emergency=True)
                
        # 2. Sell all Spot BTC
        if hasattr(engine, 'btc_hodl_balance') and engine.btc_hodl_balance > 0:
            engine.sell_btc(engine.btc_hodl_balance, current_price, timestamp)
            
    def get_name(self) -> str:
        return f"PolicyLayer({self.current_regime.name})"
