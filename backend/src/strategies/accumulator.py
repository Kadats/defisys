"""
BTC Accumulator Strategy (V15 - The Satoshi Maximizer).

Strategy designed for BTC accumulators who want to maximize BTC holdings:
- BULL MODE (Prediction == 1, High Confidence): Leverage aggressively to acquire more BTC
- DEFENSE MODE (Prediction == 0): De-leverage, repay debt, return to 100% equity BTC HODL
- DIP BUYER: Use USD reserve to buy BTC when oversold (RSI < 30)

Key Principle: NEVER sell the core BTC stack. Only exit to repay debt.
"""
import pandas as pd
import logging
from typing import TYPE_CHECKING

from .base import BaseStrategy
from ..core import LOAN_TO_VALUE_RATIO
from ..config import (
    GAS_RESERVE_USD,
    SIMULATED_GAS_FEE_USD,
    SAFE_HF_AFTER_BORROW,
    ML_CONFIDENCE_THRESHOLD,
    MAX_DEBT_RATIO
)

if TYPE_CHECKING:
    from ..core import TradingEngine

logger = logging.getLogger(__name__)

# Strategy-specific constants
BULL_CONFIDENCE_THRESHOLD = 0.65  # Only leverage if prediction probability > 65%
TARGET_SELL_MULTIPLIER = 1.05     # Single-sided LP target: 5% above current price
DIP_BUY_RSI_THRESHOLD = 30        # Buy dips when RSI < 30
MIN_USD_FOR_DIP_BUY = 100         # Minimum USD to trigger dip buying


class AccumulatorStrategy(BaseStrategy):
    """
    BTC Accumulator Strategy (V15).
    
    Designed for users who want to maximize BTC holdings:
    - Bull Mode: Leverage to acquire more BTC satoshis
    - Defense Mode: De-leverage to pure BTC HODL (no debt)
    - Never sells BTC except to repay debt
    - Uses USD reserve to buy dips when oversold
    """
    
    def execute(self, row: pd.Series, engine: 'TradingEngine', timestamp: pd.Timestamp) -> None:
        """
        Execute the BTC Accumulator strategy for a single time step.
        
        Args:
            row: Current market data with indicators and predictions
            engine: TradingEngine instance with portfolio state
            timestamp: Current timestamp
        """
        current_price = row['Close']
        prediction = int(row.get('prediction', 0))
        prediction_proba = float(row.get('prediction_proba', 0.0))
        rsi = float(row.get('RSI', 50))
        
        # --- MODE DETECTION ---
        is_bull_mode = (prediction == 1) and (prediction_proba > BULL_CONFIDENCE_THRESHOLD)
        is_defense_mode = (prediction == 0)
        
        # --- DEFENSE MODE: De-leverage and return to pure BTC HODL ---
        if is_defense_mode and (len(engine.active_lps) > 0 or engine.total_debt_usd > 0):
            self._execute_defense_mode(engine, current_price, timestamp)
            return
        
        # --- DIP BUYER: Use USD reserve when oversold ---
        if is_defense_mode and engine.usd_balance > MIN_USD_FOR_DIP_BUY and rsi < DIP_BUY_RSI_THRESHOLD:
            self._buy_the_dip(engine, current_price, timestamp)
            return
        
        # --- BULL MODE: Aggressive leverage to accumulate BTC ---
        if is_bull_mode and engine.total_debt_usd == 0:
            self._execute_bull_entry(engine, current_price, timestamp, row)
            return
        
        # --- MAINTENANCE: Check LP health ---
        if len(engine.active_lps) > 0:
            self._maintain_positions(engine, current_price, timestamp)
    
    def _execute_defense_mode(
        self, 
        engine: 'TradingEngine', 
        current_price: float, 
        timestamp: pd.Timestamp
    ) -> None:
        """
        Defense Mode: Close all LPs and repay debt.
        Goal: Return to 100% equity (0% debt) BTC HODL state.
        """
        logger.info(f"[{timestamp.date()}] DEFENSE MODE: De-leveraging to pure BTC HODL...")
        
        # Step 1: Close all active LPs
        lps_to_close = list(engine.active_lps)  # Copy to avoid modification during iteration
        for lp in lps_to_close:
            logger.info(f"[{timestamp.date()}] Closing LP {lp['id']} to de-leverage...")
            engine.close_lp(lp['id'], current_price, timestamp, is_emergency=False)
        
        # Step 2: Repay debt with available USD
        if engine.total_debt_usd > 0:
            # Use all available USD (minus gas reserve) to repay debt
            safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
            
            if safe_balance >= SIMULATED_GAS_FEE_USD:
                # Pay gas for repayment transaction
                engine.usd_balance -= SIMULATED_GAS_FEE_USD
                safe_balance -= SIMULATED_GAS_FEE_USD
                
                # Repay as much debt as possible
                repay_amount = min(safe_balance, engine.total_debt_usd)
                
                if repay_amount > 0:
                    engine.total_debt_usd -= repay_amount
                    engine.usd_balance -= repay_amount
                    logger.info(
                        f"[{timestamp.date()}] DEBT REPAID: ${repay_amount:.2f}. "
                        f"Remaining Debt: ${engine.total_debt_usd:.2f}"
                    )
                else:
                    logger.warning(f"[{timestamp.date()}] Insufficient USD to repay debt after gas.")
            
            # Step 3: If we still have debt but have BTC, we might need to sell some BTC
            # (This is a last resort to avoid liquidation)
            if engine.total_debt_usd > 10 and engine.btc_hodl_balance > 0:
                btc_value_needed = engine.total_debt_usd / current_price
                btc_to_sell = min(btc_value_needed * 1.05, engine.btc_hodl_balance)  # 5% buffer
                
                if btc_to_sell > 0:
                    usd_received = btc_to_sell * current_price
                    engine.btc_hodl_balance -= btc_to_sell
                    engine.usd_balance += usd_received
                    
                    logger.warning(
                        f"[{timestamp.date()}] EMERGENCY BTC SALE: Sold {btc_to_sell:.6f} BTC "
                        f"to repay remaining debt. This is a last resort."
                    )
                    
                    # Repay the debt
                    repay_amount = min(engine.usd_balance, engine.total_debt_usd)
                    engine.total_debt_usd -= repay_amount
                    engine.usd_balance -= repay_amount
        
        # Step 4: Convert any remaining USD to BTC if we're fully de-leveraged
        if engine.total_debt_usd == 0 and engine.usd_balance > 50:
            remaining_usd = engine.usd_balance - GAS_RESERVE_USD
            if remaining_usd > 10:
                engine.buy_and_hodl(remaining_usd, current_price, timestamp)
                logger.info(
                    f"[{timestamp.date()}] Converted remaining ${remaining_usd:.2f} to BTC. "
                    f"Now pure BTC HODL."
                )
    
    def _buy_the_dip(
        self, 
        engine: 'TradingEngine', 
        current_price: float, 
        timestamp: pd.Timestamp
    ) -> None:
        """
        Dip Buyer: Use USD reserve to buy BTC when oversold (RSI < 30).
        """
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        if safe_balance > 10:
            logger.info(
                f"[{timestamp.date()}] DIP BUY: RSI oversold. "
                f"Buying BTC with ${safe_balance:.2f}"
            )
            engine.buy_and_hodl(safe_balance, current_price, timestamp)
    
    def _execute_bull_entry(
        self, 
        engine: 'TradingEngine', 
        current_price: float, 
        timestamp: pd.Timestamp,
        row: pd.Series
    ) -> None:
        """
        Bull Mode Entry: Leverage aggressively to accumulate more BTC.
        
        Steps:
        1. Buy spot BTC with available USD
        2. Borrow USDT against BTC collateral (safe LTV)
        3. Buy more BTC with borrowed funds
        4. Open single-sided BTC LP at target price (1.05x)
        """
        logger.info(f"[{timestamp.date()}] BULL MODE: Leveraging to accumulate BTC...")
        
        # Step 1: Buy spot BTC with available USD
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        if safe_balance > 10:
            # Keep 20% as reserve, use 80% for entry
            entry_capital = safe_balance * 0.80
            engine.buy_and_hodl(entry_capital, current_price, timestamp)
            logger.info(f"[{timestamp.date()}] Spot Entry: Bought BTC with ${entry_capital:.2f}")
        
        # Step 2: Borrow USDT against BTC collateral
        if engine.btc_hodl_balance > 0:
            collateral_value = engine.btc_hodl_balance * current_price
            
            # Calculate safe borrow amount (conservative 40% LTV)
            max_borrow = collateral_value * MAX_DEBT_RATIO
            
            # Ensure we maintain safe Health Factor
            projected_debt = engine.total_debt_usd + max_borrow
            projected_hf = (collateral_value * 0.80) / projected_debt if projected_debt > 0 else 999.0
            
            if projected_hf >= SAFE_HF_AFTER_BORROW:
                engine.total_debt_usd += max_borrow
                engine.usd_balance += max_borrow
                logger.info(
                    f"[{timestamp.date()}] LEVERAGE: Borrowed ${max_borrow:.2f} "
                    f"(Projected HF: {projected_hf:.2f})"
                )
                
                # Step 3: Use half of borrowed funds to buy more BTC
                btc_buy_amount = max_borrow * 0.50
                if btc_buy_amount > 10:
                    engine.buy_and_hodl(btc_buy_amount, current_price, timestamp)
                    logger.info(f"[{timestamp.date()}] Bought more BTC with ${btc_buy_amount:.2f} borrowed USDT")
                
                # Step 4: Open single-sided BTC LP with the other half
                lp_capital = max_borrow * 0.50
                if lp_capital > 10:
                    # Single-sided LP range: current price to 5% above
                    range_lower = current_price
                    range_upper = current_price * TARGET_SELL_MULTIPLIER
                    
                    engine.open_lp(
                        lp_capital, 
                        range_lower, 
                        range_upper, 
                        current_price, 
                        timestamp, 
                        strategy="ACCUMULATOR_BULL"
                    )
                    logger.info(
                        f"[{timestamp.date()}] Opened BTC LP: Range ${range_lower:.2f} - ${range_upper:.2f}"
                    )
            else:
                logger.warning(
                    f"[{timestamp.date()}] Cannot borrow safely. "
                    f"Projected HF ({projected_hf:.2f}) < {SAFE_HF_AFTER_BORROW}"
                )
    
    def _maintain_positions(
        self, 
        engine: 'TradingEngine', 
        current_price: float, 
        timestamp: pd.Timestamp
    ) -> None:
        """
        Maintain existing LP positions: Close if out of range or hit target.
        """
        lps_to_close = []
        
        for lp in engine.active_lps:
            # Check if LP is out of range (above upper bound = take profit)
            if current_price >= lp['range_upper']:
                logger.info(
                    f"[{timestamp.date()}] LP {lp['id']} hit take-profit target "
                    f"(Price ${current_price:.2f} >= ${lp['range_upper']:.2f}). Closing..."
                )
                lps_to_close.append(lp['id'])
            
            # Check if LP has been out of range for too long (below range)
            elif current_price < lp['range_lower']:
                # This shouldn't happen often in bull mode, but close if it does
                logger.info(
                    f"[{timestamp.date()}] LP {lp['id']} out of range below. Closing..."
                )
                lps_to_close.append(lp['id'])
        
        # Close marked LPs
        for lp_id in lps_to_close:
            engine.close_lp(lp_id, current_price, timestamp, is_emergency=False)
