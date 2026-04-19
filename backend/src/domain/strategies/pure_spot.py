"""
Pure Spot Strategy (100% In/Out Baseline).

[Benchmark de Comparação]
Objetivo: USD (Benchmark Passivo)
Regime Ideal: N/A (Funciona como Baseline)
Risco Esperado: Médio (Spot puro, sem alavancagem)

Strategy that operates only with market buys and sells (Spot):
- BUY: 90% of USD balance if prediction_proba >= 0.54
- SELL: If Profit >= 5% OR Loss <= -5% OR prediction_proba < 0.48
- Simplicity: No DeFi, no LPs, no lending.
"""
import pandas as pd
import logging
from typing import TYPE_CHECKING
from .base import BaseStrategy

if TYPE_CHECKING:
    from backend.src.core import TradingEngine

logger = logging.getLogger(__name__)

class PureSpotStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.average_entry_price = 0.0

    def get_name(self) -> str:
        return "PureSpotStrategy"

    def execute(self, row: pd.Series, engine: 'TradingEngine', timestamp: pd.Timestamp) -> dict:
        current_price = float(row['Close'])
        prediction_proba = float(row.get('prediction_proba', 0.50))
        decision = {"action": "HOLD", "sizing": 0.0, "reason": "No signal", "expected_risk": "Low"}

        # Check for SELL signals if we hold BTC
        if engine.btc_hodl_balance > 0 and self.average_entry_price > 0:
            pnl_pct = (current_price - self.average_entry_price) / self.average_entry_price
            
            # 1. Take Profit (+5%)
            # 2. Stop Loss (-5%)
            # 3. Abort Trend (ML < 0.48)
            if pnl_pct >= 0.05 or pnl_pct <= -0.05 or prediction_proba < 0.48:
                reason = ""
                if pnl_pct >= 0.05: reason = f"Take Profit (+{pnl_pct:.2%})"
                elif pnl_pct <= -0.05: reason = f"Stop Loss ({pnl_pct:.2%})"
                else: reason = f"Abort Trend (ML {prediction_proba:.2f})"
                
                logger.info(f"[{timestamp.date()}] PureSpot SELL: {reason}")
                engine.sell_btc(engine.btc_hodl_balance, current_price, timestamp)
                self.average_entry_price = 0.0
                decision.update({"action": "SELL", "sizing": 1.0, "reason": reason, "expected_risk": "Low"})
                return decision

        # Check for BUY signal if we are in cash
        if engine.btc_hodl_balance == 0 and engine.usd_balance > 0:
            if prediction_proba >= 0.54:
                # Allocate 90% of cash
                amount_to_spend = engine.usd_balance * 0.90
                logger.info(f"[{timestamp.date()}] PureSpot BUY: ML {prediction_proba:.2f} | Amount: ${amount_to_spend:.2f}")
                engine.buy_and_hodl(amount_to_spend, current_price, timestamp)
                self.average_entry_price = current_price
                decision.update({"action": "BUY", "sizing": 0.9, "reason": f"ML {prediction_proba:.2f}", "expected_risk": "Med"})
        
        return decision
