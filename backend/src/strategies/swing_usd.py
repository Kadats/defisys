"""
Swing USD Strategy (V1 - Bear Market Capital Protector).

Strategy designed for traders who want to maximize USD holdings through swing trades:
- BUY LOW: Enter positions when market is oversold with ML confirmation
- SELL HIGH: Take profit at +10% or cut losses (Hard Stop: -8%, Smart Stop: ML<25%)
- Capital Preservation: Focus on protecting USD during bear markets
- No DeFi/Leverage: Pure spot trading only (no AAVE, no LPs)

Key Principle: Buy the dip, sell the rip. Maximize USD balance, not BTC holdings.
"""
import pandas as pd
import logging
from typing import TYPE_CHECKING

from .base import BaseStrategy
from ..config import (
    GAS_RESERVE_USD,
    SIMULATED_GAS_FEE_USD,
)

if TYPE_CHECKING:
    from ..core import TradingEngine

logger = logging.getLogger(__name__)

# ============================================================================
# SWING STRATEGY CONSTANTS
# ============================================================================
# Entry Signals
ENTRY_RSI_MAX = 40                    # Only buy when RSI < 40 (oversold)
ENTRY_CONFIDENCE_THRESHOLD = 0.60     # ML must confirm reversal (>= 60%)
MOMENTUM_CONFIDENCE_THRESHOLD = 0.75  # High confidence: Buy regardless of RSI

# Exit Signals (Take Profit / Stop Loss)
TAKE_PROFIT_PCT = 0.10                # Take profit at +10% from entry
STOP_LOSS_CONFIDENCE = 0.25           # Smart stop loss: ML predicts severe drop (lowered from 0.40)
HARD_STOP_LOSS_PCT = -0.08            # Hard stop loss: -8% from entry (protection against severe drawdown)

# Position Sizing
POSITION_SIZE_PERCENT = 0.80          # Use 80% of safe balance per entry (maximize returns on detected opportunities)
MIN_POSITION_USD = 10.0               # Minimum USD per position (exchange minimum)

# Cool-Down (Anti Over-Trading)
COOLDOWN_HOURS = 8                    # Hours to wait between trades (8h = 2 candles of 4h)

# Reserve Management
MIN_RESERVE_USD = 50.0                # Minimum USD to keep as reserve


class SwingUSDStrategy(BaseStrategy):
    """
    Swing USD Strategy (V1 - Bear Market Capital Protector).
    
    Designed for traders who want to maximize USD holdings:
    - Entry: Buy when (RSI < 40 AND ML confidence > 60%) OR (ML confidence > 75%)
    - Take Profit: Sell when price is +10% above average entry
    - Smart Stop Loss: Sell when ML confidence drops below 25% (severe downtrend prediction)
    - Hard Stop Loss: Sell when price drops -8% from entry (capital preservation)
    - No leverage, no DeFi, pure spot trading
    """
    
    def __init__(self, use_llm: bool = False):
        """
        Initialize strategy with state tracking.
        
        Args:
            use_llm: If True, consult Gemini API for decisions. If False, use heuristic only (default).
        """
        super().__init__()
        self.average_entry_price = 0.0    # Track average entry price for P&L calculations
        self.last_trade_time = None        # Track last trade timestamp for cool-down
        self.use_llm = use_llm             # LLM toggle (not used in V1, reserved for future)
    
    def _is_cooldown_passed(self, current_time: pd.Timestamp) -> bool:
        """
        Check if enough time has passed since the last trade (cool-down period).
        
        Args:
            current_time: Current timestamp
        
        Returns:
            True if cool-down period has passed or no previous trade, False otherwise
        """
        if self.last_trade_time is None:
            return True
        
        time_delta = current_time - self.last_trade_time
        hours_since_last_trade = time_delta.total_seconds() / 3600
        
        cooldown_passed = hours_since_last_trade >= COOLDOWN_HOURS
        
        if not cooldown_passed:
            hours_remaining = COOLDOWN_HOURS - hours_since_last_trade
            logger.debug(
                f"[{current_time.date()}] ⏳ COOL-DOWN ACTIVE: Last trade was {hours_since_last_trade:.1f}h ago. "
                f"Need to wait {hours_remaining:.1f}h more (Total: {COOLDOWN_HOURS}h)"
            )
        
        return cooldown_passed
    
    def _check_exit_conditions(self, current_price: float, prediction_proba: float, timestamp: pd.Timestamp) -> dict:
        """
        Check if we should exit the current position (Take Profit or Stop Loss).
        
        Args:
            current_price: Current BTC price in USD
            prediction_proba: ML model confidence (0.0 to 1.0)
            timestamp: Current timestamp for logging
        
        Returns:
            dict with 'type' and 'reason' if exit signal, None otherwise
        """
        # No position, no exit
        if self.average_entry_price == 0.0:
            return None
        
        # Calculate current P&L
        pnl_pct = (current_price - self.average_entry_price) / self.average_entry_price
        
        # EXIT CONDITION 1: TAKE PROFIT (+10%)
        if pnl_pct >= TAKE_PROFIT_PCT:
            logger.info(
                f"[{timestamp.date()}] 💰 TAKE PROFIT TRIGGER: Current=${current_price:.2f}, "
                f"Entry=${self.average_entry_price:.2f}, Profit={pnl_pct:.2%}"
            )
            return {
                'type': 'TAKE_PROFIT',
                'reason': f'Take profit at +{pnl_pct:.2%} (Target: +{TAKE_PROFIT_PCT:.2%})'
            }
        
        # EXIT CONDITION 2: HARD STOP LOSS (-8% from entry)
        if pnl_pct <= HARD_STOP_LOSS_PCT:
            logger.info(
                f"[{timestamp.date()}] 🚨 HARD STOP LOSS TRIGGER: Current=${current_price:.2f}, "
                f"Entry=${self.average_entry_price:.2f}, Loss={pnl_pct:.2%}. Cutting losses to preserve capital."
            )
            return {
                'type': 'HARD_STOP_LOSS',
                'reason': f'Hard stop loss at {pnl_pct:.2%} (Limit: {HARD_STOP_LOSS_PCT:.2%})'
            }
        
        # EXIT CONDITION 3: SMART STOP LOSS (ML confirms severe downtrend)
        if prediction_proba < STOP_LOSS_CONFIDENCE:
            logger.info(
                f"[{timestamp.date()}] 🛑 SMART STOP LOSS TRIGGER: ML Confidence={prediction_proba:.2%} < {STOP_LOSS_CONFIDENCE:.2%}. "
                f"Current P&L={pnl_pct:.2%}. ML predicts severe drop, exiting position."
            )
            return {
                'type': 'SMART_STOP_LOSS',
                'reason': f'ML predicts severe drop (confidence={prediction_proba:.2%}). Current P&L={pnl_pct:.2%}'
            }
        
        # No exit signal
        logger.debug(
            f"[{timestamp.date()}] 📊 HOLDING: Entry=${self.average_entry_price:.2f}, "
            f"Current=${current_price:.2f}, P&L={pnl_pct:.2%}, ML={prediction_proba:.2%}"
        )
        return None
    
    def _check_entry_conditions(self, rsi: float, prediction_proba: float, timestamp: pd.Timestamp) -> dict:
        """
        Check if we should enter a new position (buy signal).
        
        Entry Logic:
        1. MOMENTUM ENTRY: High ML confidence (>= 75%) → Buy regardless of RSI
        2. DIP ENTRY: Medium ML confidence (>= 60%) + RSI < 40 → Buy on dip
        
        Args:
            rsi: Current RSI indicator value
            prediction_proba: ML model confidence (0.0 to 1.0)
            timestamp: Current timestamp for logging
        
        Returns:
            dict with 'type' and 'reason' if entry signal, None otherwise
        """
        # ENTRY CONDITION 1: MOMENTUM ENTRY (High Confidence)
        if prediction_proba >= MOMENTUM_CONFIDENCE_THRESHOLD:
            logger.info(
                f"[{timestamp.date()}] 🚀 MOMENTUM ENTRY: ML Confidence={prediction_proba:.2%}, "
                f"RSI={rsi:.1f}. High conviction trade!"
            )
            return {
                'type': 'MOMENTUM',
                'reason': f'High ML confidence ({prediction_proba:.2%}) - Buy regardless of RSI'
            }
        
        # ENTRY CONDITION 2: DIP ENTRY (Medium Confidence + Oversold)
        if prediction_proba >= ENTRY_CONFIDENCE_THRESHOLD and rsi < ENTRY_RSI_MAX:
            logger.info(
                f"[{timestamp.date()}] 📉 DIP ENTRY: ML Confidence={prediction_proba:.2%}, "
                f"RSI={rsi:.1f}. Buying the dip!"
            )
            return {
                'type': 'DIP',
                'reason': f'ML confirms reversal ({prediction_proba:.2%}) + RSI oversold ({rsi:.1f} < {ENTRY_RSI_MAX})'
            }
        
        # No entry signal
        logger.debug(
            f"[{timestamp.date()}] 🔍 NO ENTRY: ML={prediction_proba:.2%}, RSI={rsi:.1f}. "
            f"Waiting for better setup..."
        )
        return None
    
    def execute(self, row: pd.Series, engine: 'TradingEngine', timestamp: pd.Timestamp) -> None:
        """
        Execute the Swing USD strategy for a single time step.
        
        Flow:
        1. If holding BTC: Check exit conditions (Take Profit / Stop Loss)
        2. If 100% cash: Check entry conditions (Momentum / Dip Entry)
        3. Enforce cool-down between trades
        
        Args:
            row: Current market data with indicators and predictions
            engine: TradingEngine instance with portfolio state
            timestamp: Current timestamp
        """
        current_price = row['Close']
        
        # Handle NaN values in predictions (from missing data in early timeseries)
        proba_value = row.get('prediction_proba', 0.0)
        prediction_proba = float(proba_value) if not pd.isna(proba_value) else 0.0
        
        rsi_value = row.get('RSI', 50)
        rsi = float(rsi_value) if not pd.isna(rsi_value) else 50
        
        # ==================== PART 1: EXIT LOGIC (Sell BTC if holding) ====================
        if engine.btc_hodl_balance > 0:
            exit_signal = self._check_exit_conditions(current_price, prediction_proba, timestamp)
            
            if exit_signal:
                # SELL 100% of BTC position
                btc_to_sell = engine.btc_hodl_balance
                usd_received = engine.sell_btc(btc_to_sell, current_price, timestamp)
                
                if usd_received > 0:
                    # Calculate realized P&L
                    cost_basis = self.average_entry_price * btc_to_sell
                    realized_pnl = usd_received - cost_basis
                    realized_pnl_pct = (realized_pnl / cost_basis) if cost_basis > 0 else 0.0
                    
                    logger.info(
                        f"[{timestamp.date()}] ✅ {exit_signal['type']}: Sold {btc_to_sell:.8f} BTC @ ${current_price:.2f}. "
                        f"Received ${usd_received:.2f}. Realized P&L: ${realized_pnl:.2f} ({realized_pnl_pct:.2%})"
                    )
                    logger.info(f"[{timestamp.date()}] 📝 Reason: {exit_signal['reason']}")
                    
                    # Reset average entry price (now 100% cash)
                    self.average_entry_price = 0.0
                    self.last_trade_time = timestamp
                else:
                    logger.error(
                        f"[{timestamp.date()}] ❌ Failed to sell BTC. Check engine.sell_btc() logs."
                    )
                
                return  # Exit after selling
        
        # ==================== PART 2: ENTRY LOGIC (Buy BTC if 100% cash) ====================
        # Only consider entry if we're 100% in cash
        if engine.btc_hodl_balance == 0:
            # Check cool-down before entering new position
            if not self._is_cooldown_passed(timestamp):
                logger.debug(
                    f"[{timestamp.date()}] Skipping entry due to active cool-down period."
                )
                return
            
            # Check entry conditions
            entry_signal = self._check_entry_conditions(rsi, prediction_proba, timestamp)
            
            if entry_signal:
                # Calculate position size (80% of safe balance to maximize returns on detected opportunities)
                safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD - MIN_RESERVE_USD)
                target_amount = safe_balance * POSITION_SIZE_PERCENT
                
                # Validate minimum position size
                if target_amount < MIN_POSITION_USD:
                    logger.debug(
                        f"[{timestamp.date()}] Capital insuficiente para entrada. "
                        f"Safe Balance=${safe_balance:.2f}, Target=${target_amount:.2f}, "
                        f"Mínimo=${MIN_POSITION_USD:.2f}"
                    )
                    return
                
                # Ensure we don't exceed available balance
                final_amount = min(target_amount, safe_balance)
                
                # Execute buy
                initial_btc = engine.btc_hodl_balance
                engine.buy_and_hodl(final_amount, current_price, timestamp)
                btc_bought = engine.btc_hodl_balance - initial_btc
                
                if btc_bought > 0:
                    # Update average entry price
                    self.average_entry_price = current_price
                    self.last_trade_time = timestamp
                    
                    logger.info(
                        f"[{timestamp.date()}] ✅ {entry_signal['type']}: Bought {btc_bought:.8f} BTC @ ${current_price:.2f}. "
                        f"Spent ${final_amount:.2f}. Entry Price=${self.average_entry_price:.2f}"
                    )
                    logger.info(f"[{timestamp.date()}] 📝 Reason: {entry_signal['reason']}")
                else:
                    logger.error(
                        f"[{timestamp.date()}] ❌ Failed to buy BTC. Check engine.buy_and_hodl() logs."
                    )
