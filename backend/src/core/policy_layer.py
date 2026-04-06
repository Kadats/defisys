import pandas as pd
from typing import TYPE_CHECKING

from backend.src.strategies.base import BaseStrategy
from backend.src.strategies.btc_lite import BTCLiteStrategy
from backend.src.strategies.swing_usd import SwingUSDStrategy
from backend.src.ai.regime_classifier import MarketRegime, detect_regime

if TYPE_CHECKING:
    from backend.src.core.trading_engine import TradingEngine

class PolicyLayerStrategy(BaseStrategy):
    """
    Policy Layer that dynamically routes execution to specialized strategies
    based on the current market regime detected by the RegimeClassifier.
    """
    
    def __init__(self, use_llm: bool = False):
        self.bull_strategy = BTCLiteStrategy()
        self.bear_strategy = SwingUSDStrategy(use_llm=use_llm)
        self.sideways_strategy = SwingUSDStrategy(use_llm=use_llm) # SwingUSD can handle mean reversion/sideways
        self.current_regime = MarketRegime.UNCERTAIN

    def execute(self, row: pd.Series, engine: 'TradingEngine', timestamp: pd.Timestamp) -> dict:
        """
        Detects regime and routes to the appropriate strategy.
        Forces abstention (100% USD Cash) if the regime is UNCERTAIN.
        """
        # Detect the current market regime
        self.current_regime = detect_regime(row)
        current_price = float(row.get('Close', 0.0))
        
        if self.current_regime == MarketRegime.BULL:
            return self.bull_strategy.execute(row, engine, timestamp)
            
        elif self.current_regime == MarketRegime.BEAR:
            return self.bear_strategy.execute(row, engine, timestamp)
            
        elif self.current_regime == MarketRegime.SIDEWAYS:
            return self.sideways_strategy.execute(row, engine, timestamp)
            
        elif self.current_regime == MarketRegime.UNCERTAIN:
            # Force Abstention: Move to 100% USD Cash
            self._force_100_percent_cash(engine, current_price, timestamp)
            
            return {
                "action": "ABSTAIN",
                "sizing": 0.0,
                "reason": "Regime is UNCERTAIN. Forced 100% Cash.",
                "expected_risk": "Low"
            }
            
        # Fallback
        return {
            "action": "HOLD",
            "sizing": 0.0,
            "reason": "Unknown regime fallback.",
            "expected_risk": "Med"
        }

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
