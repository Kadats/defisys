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
MOMENTUM_CONFIDENCE_THRESHOLD = 0.65  # High confidence: Buy regardless of RSI (lowered from 0.70)
MOMENTUM_RSI_MAX = 75                 # Max RSI acceptable in momentum mode (relaxed from 70)
DIP_CONFIDENCE_THRESHOLD = 0.55       # Medium confidence: Buy on dips (relaxed from 0.60)
DIP_RSI_MAX = 60                      # Max RSI for dip entry (relaxed from 55)
TARGET_SELL_MULTIPLIER = 1.05         # Single-sided LP target: 5% above current price
DEFENSE_RSI_THRESHOLD = 35            # Extreme oversold in defense mode (relaxed from 30)
MIN_USD_FOR_DIP_BUY = 100             # Minimum USD to trigger dip buying
MIN_RESERVE_USD = 200.0               # Capital reserve to avoid full depletion
POSITION_SIZE_PERCENT = 0.10          # Conservative position sizing: 10% per entry (was 80% causing all-in)
MIN_POSITION_USD = 10.0               # Minimum USD per position (Binance minimum)

# COOL-DOWN MECHANISM (Anti Over-Trading) - V18 Quantitative Refinement
COOLDOWN_HOURS = 12                   # Hours to wait between trades (reduced from 24 to 12 hours for more activity)
COOLDOWN_CANDLES_4H = 3               # Equivalent in 4h candles (12h / 4h = 3 candles)


class AccumulatorStrategy(BaseStrategy):
    """
    BTC Accumulator Strategy (V18 - Cool-Down Refinement).
    
    Designed for users who want to maximize BTC holdings:
    - Momentum Entry: High ML confidence (>75%) → Buy regardless of RSI
    - Dip Entry: Medium ML confidence (>60%) → Buy on pullbacks (RSI<55)
    - Defense Mode: De-leverage to pure BTC HODL (no debt)
    - Never sells BTC except to repay debt
    - Uses USD reserve to buy extreme dips when oversold (RSI<30)
    - Cool-Down: 24h minimum between trades to prevent over-trading
    """
    
    def __init__(self):
        """Initialize strategy with cool-down tracking."""
        super().__init__()
        self.last_trade_time = None  # Track last trade timestamp for cool-down
    
    def _is_cooldown_passed(self, current_time: pd.Timestamp) -> bool:
        """
        Check if enough time has passed since the last trade (cool-down period).
        
        This prevents over-trading by enforcing a minimum time between entries.
        
        Args:
            current_time: Current timestamp
        
        Returns:
            True if cool-down period has passed or no previous trade, False otherwise
        """
        if self.last_trade_time is None:
            return True  # No previous trade, cool-down not applicable
        
        # Calculate time difference in hours
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
    
    def _analyze_market_entry(self, prediction_proba: float, rsi: float, timestamp: pd.Timestamp) -> dict:
        """
        Analyze market conditions and determine if we should enter a position.
        
        Two-level entry logic based on ML confidence:
        1. MOMENTUM ENTRY (High Confidence): proba > 0.75, RSI < 70
           - When ML is very confident, don't wait for deep pullbacks
        2. DIP ENTRY (Medium Confidence): proba > 0.60, RSI < 55
           - When ML is moderately confident, wait for better prices
        
        Args:
            prediction_proba: ML model confidence (0.0 to 1.0)
            rsi: Current RSI indicator value
            timestamp: Current timestamp for logging
        
        Returns:
            dict with 'type' and 'reason' if entry signal, None otherwise
        """
        # Level 1: MOMENTUM ENTRY (Alta Confiança)
        if prediction_proba > MOMENTUM_CONFIDENCE_THRESHOLD:
            if rsi < MOMENTUM_RSI_MAX:
                logger.info(
                    f"[{timestamp.date()}] ✅ MOMENTUM ENTRY: ML Confidence={prediction_proba:.2%}, "
                    f"RSI={rsi:.1f}. High conviction trade!"
                )
                return {
                    'type': 'MOMENTUM',
                    'reason': f'High ML confidence ({prediction_proba:.2%}) with RSI={rsi:.1f}'
                }
            else:
                logger.info(
                    f"[{timestamp.date()}] ⚠️  HIGH CONFIDENCE but RSI={rsi:.1f} > {MOMENTUM_RSI_MAX}. "
                    f"Market may be overbought. Waiting..."
                )
        
        # Level 2: DIP ENTRY (Média Confiança)
        elif prediction_proba > DIP_CONFIDENCE_THRESHOLD:
            if rsi < DIP_RSI_MAX:
                logger.info(
                    f"[{timestamp.date()}] ✅ DIP ENTRY: ML Confidence={prediction_proba:.2%}, "
                    f"RSI={rsi:.1f}. Good risk/reward on pullback!"
                )
                return {
                    'type': 'DIP',
                    'reason': f'Medium ML confidence ({prediction_proba:.2%}) with favorable RSI={rsi:.1f}'
                }
            else:
                logger.debug(
                    f"[{timestamp.date()}] Medium confidence ({prediction_proba:.2%}) but RSI={rsi:.1f} "
                    f"not low enough (need <{DIP_RSI_MAX}). Waiting for pullback..."
                )
        else:
            # Low confidence - no entry
            logger.debug(
                f"[{timestamp.date()}] No entry signal: ML Confidence={prediction_proba:.2%} "
                f"below threshold ({DIP_CONFIDENCE_THRESHOLD:.2%})"
            )
        
        return None
    
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
        
        # --- DEFENSE MODE: De-leverage only on real risk (HF or cash crunch) ---
        has_leverage = (len(engine.active_lps) > 0 or engine.total_debt_usd > 0)
        is_defense_mode = (
            engine.health_factor < 1.5 or
            (engine.usd_balance < 50 and has_leverage)
        )
        if is_defense_mode and has_leverage:
            self._execute_defense_mode(engine, current_price, timestamp)
            return
        
        # --- COOL-DOWN CHECK: Prevent over-trading by enforcing minimum time between entries ---
        if not self._is_cooldown_passed(timestamp):
            logger.debug(f"[{timestamp.date()}] Skipping entry due to active cool-down period.")
            # Still maintain existing positions even during cool-down
            if len(engine.active_lps) > 0:
                self._maintain_positions(engine, current_price, timestamp)
            return
        
        # --- ANALYZE MARKET: Check if we should enter a position ---
        entry_signal = self._analyze_market_entry(prediction_proba, rsi, timestamp)
        
        # --- PRIMARY: BULL ENTRY WITH DEFI (Momentum or DIP) ---
        if entry_signal and engine.usd_balance > MIN_USD_FOR_DIP_BUY:
            # HIGH CONFIDENCE: OPEN_LP + BORROW (if conditions safe)
            if entry_signal['type'] == 'MOMENTUM' and engine.total_debt_usd == 0:
                logger.info(f"[{timestamp.date()}] 🔥 MOMENTUM + HIGH CONFIDENCE: Executing full DeFi strategy (LP + Borrow)")
                self._execute_bull_entry(engine, current_price, timestamp, row, entry_signal)
                self.last_trade_time = timestamp
                return
            
            # MEDIUM CONFIDENCE: Try OPEN_LP only (risky borrow prevented)
            elif entry_signal['type'] == 'DIP' and engine.total_debt_usd == 0:
                logger.info(f"[{timestamp.date()}] 📍 DIP + MEDIUM CONFIDENCE: Opening LP for yield farming")
                self._open_lp_conservative(engine, current_price, timestamp, entry_signal)
                self.last_trade_time = timestamp
                return
            
            # FALLBACK: If already leveraged or conditions not ideal, just buy spot
            else:
                logger.info(
                    f"[{timestamp.date()}] ✓ SIGNAL ({entry_signal['type']}) but DeFi conditions not met. "
                    f"Debt: ${engine.total_debt_usd:.2f}. Doing simple buy."
                )
                self._simple_spot_buy(engine, current_price, timestamp)
                self.last_trade_time = timestamp
                return
        
        # --- SECONDARY: EXTREME DIP BUYER (even without high confidence signal) ---
        if engine.usd_balance > MIN_USD_FOR_DIP_BUY and rsi < DEFENSE_RSI_THRESHOLD:
            logger.info(
                f"[{timestamp.date()}] EXTREME DIP: RSI={rsi:.1f} < {DEFENSE_RSI_THRESHOLD}. "
                f"Buying with available USD."
            )
            self._dip_buy(engine, current_price, timestamp)
            self.last_trade_time = timestamp
            return
        
        # --- TERTIARY: If we have existing LPs, maintain them ---
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
                # CRITICAL FIX: Validate repay_amount never exceeds available balance
                repay_amount = min(safe_balance, engine.total_debt_usd)
                repay_amount = min(repay_amount, engine.usd_balance)  # Double-check: never exceed actual USD balance
                
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
        
        # Step 4: Convert some USD to BTC if we're fully de-leveraged
        if engine.total_debt_usd == 0 and engine.usd_balance > 50:
            remaining_usd = engine.usd_balance - GAS_RESERVE_USD
            if remaining_usd > MIN_POSITION_USD:
                # Only convert a portion to preserve capital for future entries
                defense_convert_amount = min(remaining_usd * 0.30, remaining_usd * 0.50)  # Max 50% of remaining
                # CRITICAL FIX: Validate conversion amount never exceeds available USD
                defense_convert_amount = min(defense_convert_amount, engine.usd_balance - GAS_RESERVE_USD)
                if defense_convert_amount >= MIN_POSITION_USD:
                    engine.buy_and_hodl(defense_convert_amount, current_price, timestamp)
                    logger.info(
                        f"[{timestamp.date()}] Converted ${defense_convert_amount:.2f} to BTC (30% of remaining). "
                        f"Preserving capital for future entries. Balance: ${engine.usd_balance:.2f}"
                    )
    
    def _simple_spot_buy(
        self,
        engine: 'TradingEngine',
        current_price: float,
        timestamp: pd.Timestamp
    ) -> None:
        """
        Simple spot BTC buy for when DeFi conditions are not met.
        This is a fallback when we don't want to use leverage/LP.
        """
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        if safe_balance > MIN_POSITION_USD:
            # Allocate 15% of available USD for spot buy
            spot_amount = safe_balance * 0.15
            spot_amount = max(MIN_POSITION_USD, min(spot_amount, safe_balance * 0.50))
            
            logger.info(f"[{timestamp.date()}] SPOT BUY: Accumulating BTC with ${spot_amount:.2f} (no leverage)")
            engine.buy_and_hodl(spot_amount, current_price, timestamp)
    
    def _open_lp_conservative(
        self,
        engine: 'TradingEngine',
        current_price: float,
        timestamp: pd.Timestamp,
        entry_signal: dict
    ) -> None:
        """
        Open LP position conservatively when we have medium confidence but want to farm yields.
        
        This is a middle ground: We allocate capital to an LP position instead of just holding,
        but without aggressive borrowing (which is risky).
        """
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        if safe_balance > MIN_POSITION_USD:
            # Use smaller allocation for LP (15-20% of available)
            lp_capital = safe_balance * 0.15
            lp_capital = max(MIN_POSITION_USD, min(lp_capital, safe_balance * 0.40))
            
            # Single-sided LP range: current price to 5% above
            range_lower = current_price
            range_upper = current_price * TARGET_SELL_MULTIPLIER
            
            logger.info(
                f"[{timestamp.date()}] 🌾 OPEN_LP (Conservative): ${lp_capital:.2f} "
                f"Range: ${range_lower:.2f} - ${range_upper:.2f} (Yield Farming)"
            )
            
            engine.open_lp(
                lp_capital,
                range_lower,
                range_upper,
                current_price,
                timestamp,
                strategy="ACCUMULATOR_CONSERVATIVE_LP"
            )
            
            # Also buy some spot BTC to build position
            remaining_safe = safe_balance - lp_capital
            if remaining_safe > MIN_POSITION_USD * 2:
                spot_buy = remaining_safe * 0.20  # 20% of what's left for spot
                spot_buy = min(spot_buy, remaining_safe * 0.50)
                if spot_buy > MIN_POSITION_USD:
                    engine.buy_and_hodl(spot_buy, current_price, timestamp)
                    logger.info(f"[{timestamp.date()}] Also bought BTC spot: ${spot_buy:.2f}")
    
    def _dip_buy(
        self, 
        engine: 'TradingEngine', 
        current_price: float, 
        timestamp: pd.Timestamp
    ) -> None:
        """
        Dip Buyer: Use USD reserve to buy BTC when oversold (RSI < 30).
        Uses conservative position sizing to avoid all-in.
        """
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        if safe_balance > MIN_POSITION_USD:
            # Preserve a USD reserve to avoid draining capital in prolonged dips
            available_for_trade = max(0.0, engine.usd_balance - MIN_RESERVE_USD)
            if engine.usd_balance < MIN_RESERVE_USD:
                dip_buy_amount = MIN_POSITION_USD
            else:
                dip_buy_amount = max(MIN_POSITION_USD, available_for_trade * 0.20)
            dip_buy_amount = min(dip_buy_amount, safe_balance)
            
            logger.info(
                f"[{timestamp.date()}] DIP BUY: RSI oversold. "
                f"Buying BTC with ${dip_buy_amount:.2f} (20% of available)"
            )
            engine.buy_and_hodl(dip_buy_amount, current_price, timestamp)
    
    def _execute_bull_entry(
        self, 
        engine: 'TradingEngine', 
        current_price: float, 
        timestamp: pd.Timestamp,
        row: pd.Series,
        entry_signal: dict
    ) -> None:
        """
        Bull Mode Entry: Leverage aggressively to accumulate more BTC and farm yields.
        
        CRITICAL: This function is now the main path for DeFi operations.
        It should maximize:
        1. OPEN_LP for yield farming
        2. BORROW_USDT for leverage
        
        Risk management is strict: Never exceed safe Health Factor.
        
        Args:
            entry_signal: Dict with 'type' (MOMENTUM/DIP) and 'reason'
        """
        entry_type = entry_signal.get('type', 'UNKNOWN')
        entry_reason = entry_signal.get('reason', 'No reason provided')
        
        logger.info(
            f"[{timestamp.date()}] 🚀 BULL ENTRY ({entry_type}): {entry_reason}. "
            f"Unleashing DeFi Power! Opening LPs and Borrowing..."
        )
        
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        # Step 1: Build spot BTC position first (always allocate some to HODL)
        spot_allocation = safe_balance * 0.20  # 20% for spot buying
        spot_allocation = max(MIN_POSITION_USD, min(spot_allocation, safe_balance * 0.40))
        
        if spot_allocation > MIN_POSITION_USD:
            engine.buy_and_hodl(spot_allocation, current_price, timestamp)
            logger.info(
                f"[{timestamp.date()}] Spot Entry: Bought BTC with ${spot_allocation:.2f}. "
                f"Remaining USD: ${safe_balance - spot_allocation:.2f}"
            )
        
        # Step 2: OPEN LIQUIDITY POOL (Yield Farming)
        # Even WITHOUT borrowing, we should open LPs if we have capital
        lp_allocation = safe_balance * 0.40  # 40% for LP (larger allocation for yield farming)
        lp_allocation = max(MIN_POSITION_USD, min(lp_allocation, safe_balance * 0.60))
        lp_allocation = min(lp_allocation, engine.usd_balance - GAS_RESERVE_USD)
        
        if lp_allocation > 10:
            range_lower = current_price
            range_upper = current_price * TARGET_SELL_MULTIPLIER
            
            engine.open_lp(
                lp_allocation,
                range_lower,
                range_upper,
                current_price,
                timestamp,
                strategy="ACCUMULATOR_BULL"
            )
            logger.info(
                f"[{timestamp.date()}] 💰 OPEN LP (Bull): ${lp_allocation:.2f} "
                f"| Range: ${range_lower:.2f} - ${range_upper:.2f} (YIELD FARMING!)"
            )
        
        # Step 3: BORROW USDT for aggressive leverage (only if conditions are safe)
        if engine.btc_hodl_balance > 0:
            collateral_value = engine.btc_hodl_balance * current_price
            max_borrow = collateral_value * MAX_DEBT_RATIO  # 45% LTV
            
            # Check safe HF before borrowing
            projected_debt = engine.total_debt_usd + max_borrow
            projected_hf = (collateral_value * 0.80) / projected_debt if projected_debt > 0 else 999.0
            
            if projected_hf >= SAFE_HF_AFTER_BORROW and max_borrow > MIN_POSITION_USD:
                borrowed_amount = engine.borrow_funds(max_borrow, current_price)
                
                if borrowed_amount > 0:
                    logger.info(
                        f"[{timestamp.date()}] 🏦 BORROW: ${borrowed_amount:.2f} USDT "
                        f"(Projected HF: {projected_hf:.2f}, Safe Threshold: {SAFE_HF_AFTER_BORROW})"
                    )
                    
                    # Step 4: Use borrowed USDT for more OPEN_LP (leverage LP yield farming)
                    borrowed_lp_allocation = borrowed_amount * 0.60  # 60% of borrowed → another LP
                    borrowed_lp_allocation = min(borrowed_lp_allocation, engine.usd_balance - GAS_RESERVE_USD)
                    
                    if borrowed_lp_allocation > 10:
                        # Put this LP slightly HIGHER than current price (capture upside more)
                        range_lower_lever = current_price * 0.98  # Slightly below
                        range_upper_lever = current_price * 1.08  # 8% above (vs normal 5%)
                        
                        engine.open_lp(
                            borrowed_lp_allocation,
                            range_lower_lever,
                            range_upper_lever,
                            current_price,
                            timestamp,
                            strategy="ACCUMULATOR_LEVERAGED_LP"
                        )
                        logger.info(
                            f"[{timestamp.date()}] 🚀 LEVERAGED LP: ${borrowed_lp_allocation:.2f} "
                            f"(from borrowed funds) | Range: ${range_lower_lever:.2f} - ${range_upper_lever:.2f}"
                        )
                    
                    # Step 5: Use remaining borrowed for spot BTC (leverage spot accumulation)
                    remaining_borrowed = max(0.0, borrowed_amount - borrowed_lp_allocation)
                    borrowed_spot = remaining_borrowed * 0.70
                    borrowed_spot = min(borrowed_spot, engine.usd_balance - GAS_RESERVE_USD)
                    
                    if borrowed_spot > MIN_POSITION_USD:
                        engine.buy_and_hodl(borrowed_spot, current_price, timestamp)
                        logger.info(
                            f"[{timestamp.date()}] 📈 LEVERAGED BTC BUY: ${borrowed_spot:.2f} "
                            f"(from borrowed USDT)"
                        )
            else:
                logger.warning(
                    f"[{timestamp.date()}] Cannot borrow safely. "
                    f"Projected HF ({projected_hf:.2f}) < Safe Threshold ({SAFE_HF_AFTER_BORROW}). "
                    f"Sticking with spot + LP only."
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
