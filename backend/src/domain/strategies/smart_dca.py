"""
Smart DCA Strategy (Dollar Cost Averaging).

[Benchmark de Comparação]
Objetivo: USD (Benchmark DCA)
Regime Ideal: N/A (Baseline para testes)
Risco Esperado: Médio (Spot puro, risco de drawdown direcional)

Strategy that splits entry capital into 4 bullets (25% each):
- 1st Bullet: Entry when prediction_proba >= 0.55
- 2nd, 3rd, 4th Bullets: Entry if price drops >= 5% from average entry AND prediction_proba >= 0.52
- Take Profit: Exit 100% if profit >= 5%
- Stop Loss: Exit 100% if prediction_proba < 0.40 OR loss <= -15%
"""
import pandas as pd
import logging
from typing import TYPE_CHECKING
from .base import BaseStrategy

if TYPE_CHECKING:
    from backend.src.core import TradingEngine

logger = logging.getLogger(__name__)

class SmartDCAStrategy(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.average_entry_price = 0.0
        self.orders_placed = 0
        self.max_orders = 4
        self.bullet_size = 0.0

    def get_name(self) -> str:
        return "SmartDCAStrategy"

    def execute(self, row: pd.Series, engine: 'TradingEngine', timestamp: pd.Timestamp) -> dict:
        current_price = float(row['Close'])
        prediction_proba = float(row.get('prediction_proba', 0.50))
        decision = {"action": "HOLD", "sizing": 0.0, "reason": "No signal", "expected_risk": "Low"}

        # --- EXIT LOGIC ---
        if self.orders_placed > 0 and engine.btc_hodl_balance > 0:
            pnl_pct = (current_price - self.average_entry_price) / self.average_entry_price
            
            # Take Profit (+5%)
            # Stop Loss (Hard -15% or ML < 0.40)
            if pnl_pct >= 0.05 or pnl_pct <= -0.15 or prediction_proba < 0.40:
                reason = ""
                if pnl_pct >= 0.05: reason = f"Take Profit (+{pnl_pct:.2%})"
                elif pnl_pct <= -0.15: reason = f"Hard Stop Loss ({pnl_pct:.2%})"
                else: reason = f"ML Abort (ML {prediction_proba:.2f})"
                
                logger.info(f"[{timestamp.date()}] SmartDCA EXIT: {reason}")
                engine.sell_btc(engine.btc_hodl_balance, current_price, timestamp)
                self.average_entry_price = 0.0
                self.orders_placed = 0
                self.bullet_size = 0.0
                decision.update({"action": "SELL", "sizing": 1.0, "reason": reason, "expected_risk": "Low"})
                return decision

        # --- ENTRY LOGIC ---
        
        # 1. First Entry
        if self.orders_placed == 0 and engine.usd_balance > 0:
            if prediction_proba >= 0.55:
                self.bullet_size = engine.usd_balance * 0.25
                logger.info(f"[{timestamp.date()}] SmartDCA 1st Bullet: ML {prediction_proba:.2f} | Amount: ${self.bullet_size:.2f}")
                engine.buy_and_hodl(self.bullet_size, current_price, timestamp)
                self.average_entry_price = current_price
                self.orders_placed = 1
                decision.update({"action": "BUY", "sizing": 0.25, "reason": "1st Bullet", "expected_risk": "Med"})
                return decision

        # 2. Subsequent DCA Entries
        if 0 < self.orders_placed < self.max_orders and engine.usd_balance >= self.bullet_size:
            # Condition: price drop >= 5% AND ML >= 0.52
            if current_price <= self.average_entry_price * 0.95 and prediction_proba >= 0.52:
                logger.info(f"[{timestamp.date()}] SmartDCA Bullet {self.orders_placed + 1}: Price Drop {((current_price/self.average_entry_price)-1):.2%} | ML {prediction_proba:.2f}")
                
                # Weighted average calculation
                prev_btc = engine.btc_hodl_balance
                new_btc = self.bullet_size / current_price
                
                self.average_entry_price = (self.average_entry_price * prev_btc + current_price * new_btc) / (prev_btc + new_btc)
                
                engine.buy_and_hodl(self.bullet_size, current_price, timestamp)
                self.orders_placed += 1
                decision.update({"action": "BUY", "sizing": 0.25, "reason": f"Bullet {self.orders_placed}", "expected_risk": "Med"})
        
        return decision
