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
    ML_CONFIDENCE_THRESHOLD,
    MAX_DEBT_RATIO
)
from ..ai.llm_agent import consult_risk_agent

if TYPE_CHECKING:
    from ..core import TradingEngine

logger = logging.getLogger(__name__)

# ============================================================================
# HEALTH FACTOR (HF) CONSTANTS - Critical for DeFi Risk Management
# ============================================================================
HF_SAFE_TARGET = 2.0                  # Target HF to maintain (never borrow below this)
HF_CRITICAL = 1.3                     # Emergency threshold: Close LPs if HF drops below this

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
    
    def __init__(self, use_llm: bool = False):
        """Initialize strategy with cool-down tracking and LLM toggle.
        
        Args:
            use_llm: If True, consult Gemini API for decisions. If False, use heuristic fallback (default).
        """
        super().__init__()
        self.last_trade_time = None  # Track last trade timestamp for cool-down
        self.use_llm = use_llm  # LLM Toggle: False by default for fast backtests
    
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
        
        Flow:
        1. Check DEFENSE MODE (liquidation risk)
        2. Check COOL-DOWN (prevent over-trading)
        3. Consult LLM Risk Agent for final decision
        4. Route to appropriate execution method based on agent recommendation
        
        Args:
            row: Current market data with indicators and predictions
            engine: TradingEngine instance with portfolio state
            timestamp: Current timestamp
        """
        current_price = row['Close']
        # CRITICAL FIX: Handle NaN values in predictions (from missing data in early timeseries)
        pred_value = row.get('prediction', 0)
        prediction = int(pred_value) if not pd.isna(pred_value) else 0
        
        proba_value = row.get('prediction_proba', 0.0)
        prediction_proba = float(proba_value) if not pd.isna(proba_value) else 0.0
        
        rsi_value = row.get('RSI', 50)
        rsi = float(rsi_value) if not pd.isna(rsi_value) else 50
        
        # --- DEFENSE MODE: De-leverage only on real liquidation risk ---
        has_leverage = (len(engine.active_lps) > 0 or engine.total_debt_usd > 0)
        is_defense_mode = engine.health_factor < 1.5
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
        
        # --- CONSULT RISK AGENT: LLM-based decision making (with Trigger Architecture) ---
        # Only call Gemini API if there's a clear opportunity (save API quota)
        should_consult_gemini = (
            prediction_proba > 0.65 or  # High ML confidence
            rsi < 35 or                 # Extreme oversold
            rsi > 75                    # Extreme overbought
        )
        
        if self.use_llm and should_consult_gemini:
            # LLM is enabled: Consult Gemini API for decision
            logger.info(
                f"[{timestamp.date()}] 🎯 TRIGGER ACTIVATED: Consulting Gemini API "
                f"(ML={prediction_proba:.2%}, RSI={rsi:.1f})"
            )
            agent_context = {
                'usd_balance': engine.usd_balance,
                'btc_collateral': engine.btc_hodl_balance,
                'aave_debt': engine.total_debt_usd,
                'health_factor': engine.health_factor,
                'ml_confidence': prediction_proba,
                'rsi': rsi,
            }
            agent_decision = consult_risk_agent(agent_context)
        else:
            # LLM is disabled OR no clear signal: Use heuristic fallback
            if not self.use_llm and should_consult_gemini:
                logger.info(
                    f"[{timestamp.date()}] 🔄 [FALLBACK] IA Desligada. Usando decisão heurística instantânea. "
                    f"(ML={prediction_proba:.2%}, RSI={rsi:.1f})"
                )
                # Heuristic decision logic
                if rsi < 35:
                    # Extreme oversold: Conservative spot buy
                    agent_decision = {
                        'action': 'SPOT_ONLY',
                        'amount_pct': 0.25,
                        'reason': 'Heurística: Sobrevendido extremo (RSI<35). Compra spot conservadora.'
                    }
                elif prediction_proba > 0.65:
                    # High ML confidence: Conservative LP
                    agent_decision = {
                        'action': 'CONSERVATIVE_LP',
                        'amount_pct': 0.35,
                        'reason': 'Heurística: Alta convicção ML (>65%). LP conservadora sem alavancagem.'
                    }
                elif rsi > 75:
                    # Extreme overbought: Do nothing
                    agent_decision = {
                        'action': 'DO_NOTHING',
                        'amount_pct': 0.0,
                        'reason': 'Heurística: Sobrecomprado extremo (RSI>75). Evitar entrada.'
                    }
                else:
                    # No clear edge
                    agent_decision = {
                        'action': 'DO_NOTHING',
                        'amount_pct': 0.0,
                        'reason': 'Heurística: Sem edge claro. Aguardar melhor oportunidade.'
                    }
            else:
                # No trigger activated
                logger.debug(
                    f"[{timestamp.date()}] ⏸️  NO TRIGGER: Market sideways and ML confidence low. "
                    f"(ML={prediction_proba:.2%}, RSI={rsi:.1f})"
                )
                agent_decision = {
                    'action': 'DO_NOTHING',
                    'amount_pct': 0.0,
                    'reason': 'Market sideways and ML confidence low. Saving API quota.'
                }
        
        action = agent_decision.get('action', 'DO_NOTHING')
        amount_pct = agent_decision.get('amount_pct', 0.0)
        reason = agent_decision.get('reason', 'No reason provided')
        
        logger.info(
            f"[{timestamp.date()}] 🤖 AGENT DECISION: {action} | Allocation: {amount_pct:.0%} | {reason}"
        )
        
        # --- ROUTE BASED ON AGENT ACTION ---
        if action == 'BORROW_AND_LP':
            # Full DeFi strategy: Borrow + LP + Spot leverage
            logger.info(f"[{timestamp.date()}] 🔥 EXECUTING BORROW_AND_LP strategy with {amount_pct:.0%} allocation")
            entry_signal = {'type': 'MOMENTUM', 'reason': reason}
            self._execute_bull_entry(engine, current_price, timestamp, row, entry_signal, amount_pct)
            self.last_trade_time = timestamp
        
        elif action == 'CONSERVATIVE_LP':
            # Conservative LP without aggressive borrowing
            logger.info(f"[{timestamp.date()}] 🌾 EXECUTING CONSERVATIVE_LP strategy with {amount_pct:.0%} allocation")
            entry_signal = {'type': 'DIP', 'reason': reason}
            self._open_lp_conservative(engine, current_price, timestamp, entry_signal, amount_pct)
            self.last_trade_time = timestamp
        
        elif action == 'SPOT_ONLY':
            # Simple spot buy without leverage/LP
            logger.info(f"[{timestamp.date()}] 📍 EXECUTING SPOT_ONLY strategy with {amount_pct:.0%} allocation")
            self._simple_spot_buy(engine, current_price, timestamp, amount_pct)
            self.last_trade_time = timestamp
        
        elif action == 'DEFENSE_MODE':
            # De-leverage and reduce risk
            logger.warning(f"[{timestamp.date()}] 🛡️  EXECUTING DEFENSE_MODE: De-leveraging for safety")
            self._execute_defense_mode(engine, current_price, timestamp)
            self.last_trade_time = timestamp
        
        elif action == 'DO_NOTHING':
            # No clear signal, maintain existing positions
            logger.debug(f"[{timestamp.date()}] ⏸️  DO_NOTHING: {reason}")
            if len(engine.active_lps) > 0:
                self._maintain_positions(engine, current_price, timestamp)
        
        else:
            # Unknown action, log warning and maintain positions
            logger.warning(f"[{timestamp.date()}] ⚠️  Unknown agent action: {action}. Maintaining positions.")
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
        
        # Step 1: Close LPs only if health factor is at real liquidation risk
        if engine.health_factor < 1.5:
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
        timestamp: pd.Timestamp,
        amount_pct: float = 0.15
    ) -> None:
        """
        Simple spot BTC buy for when DeFi conditions are not met.
        This is a fallback when we don't want to use leverage/LP.
        
        Args:
            amount_pct: Percentage of safe balance to allocate (from agent or fallback default)
        """
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        # Calculate target amount based on agent allocation
        target_amount = safe_balance * amount_pct
        
        # Validate minimum position size
        if target_amount < MIN_POSITION_USD:
            logger.debug(
                f"[{timestamp.date()}] Capital insuficiente para ordem mínima. "
                f"Target: ${target_amount:.2f} < Min: ${MIN_POSITION_USD:.2f}. Ignorando entrada."
            )
            return
        
        # Never exceed safe balance (no forced buys)
        spot_amount = min(target_amount, safe_balance)
        
        logger.info(
            f"[{timestamp.date()}] SPOT BUY: Accumulating BTC with ${spot_amount:.2f} "
            f"({amount_pct:.0%} allocation, no leverage)"
        )
        engine.buy_and_hodl(spot_amount, current_price, timestamp)
    
    def _open_lp_conservative(
        self,
        engine: 'TradingEngine',
        current_price: float,
        timestamp: pd.Timestamp,
        entry_signal: dict,
        amount_pct: float = 0.15
    ) -> None:
        """
        Open LP position conservatively with correct DeFi flow:
        1. Buy Spot BTC using safe balance
        2. Add BTC as collateral to AAVE
        3. Borrow USD respecting HF_SAFE_TARGET (max 2.0)
        4. Open LP using ONLY borrowed USD (never use Spot cash for LP)
        
        This protects capital by never draining the Spot wallet for LPs.
        
        Args:
            amount_pct: Percentage of safe balance to allocate for buying BTC
        """
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        # STEP 1: Buy Spot BTC with designated allocation
        spot_allocation = safe_balance * amount_pct
        
        # Validate minimum position size
        if spot_allocation < MIN_POSITION_USD:
            logger.debug(
                f"[{timestamp.date()}] Capital insuficiente para compra spot. "
                f"Target: ${spot_allocation:.2f} < Min: ${MIN_POSITION_USD:.2f}. Ignorando entrada."
            )
            return
        
        # Never exceed safe balance
        spot_allocation = min(spot_allocation, safe_balance)
        
        logger.info(
            f"[{timestamp.date()}] 🌾 CONSERVATIVE_LP FLOW: Initiating DeFi strategy with ${spot_allocation:.2f}"
        )
        
        # STEP 1: Buy and add BTC to HODL
        engine.buy_and_hodl(spot_allocation, current_price, timestamp)
        logger.info(f"[{timestamp.date()}] STEP 1 - SPOT BUY: Bought BTC with ${spot_allocation:.2f}")
        
        # STEP 2: Add the newly bought BTC as collateral to AAVE
        if engine.btc_hodl_balance > 0:
            engine.add_collateral(engine.btc_hodl_balance)
            logger.info(
                f"[{timestamp.date()}] STEP 2 - ADD COLLATERAL: Sent {engine.btc_hodl_balance:.6f} BTC "
                f"(${engine.btc_hodl_balance * current_price:.2f}) to AAVE as collateral"
            )
        
        # STEP 3: Calculate safe borrow amount respecting HF_SAFE_TARGET
        collateral_value = engine.btc_hodl_balance * current_price
        current_debt = engine.total_debt_usd
        
        if collateral_value > 0:
            # Max borrow = (collateral * 0.80 / HF_SAFE_TARGET) - current_debt
            # This ensures: HF = (collateral * 0.80) / (current_debt + borrow) >= HF_SAFE_TARGET
            max_safe_debt = (collateral_value * 0.80) / HF_SAFE_TARGET
            borrow_amount = max(0.0, max_safe_debt - current_debt)
            
            if borrow_amount > MIN_POSITION_USD and engine.health_factor >= HF_SAFE_TARGET:
                # Only borrow if current HF is already >= HF_SAFE_TARGET
                borrowed_amount = engine.borrow_funds(borrow_amount, current_price)
                logger.info(
                    f"[{timestamp.date()}] STEP 3 - BORROW: Borrowed ${borrowed_amount:.2f} USD "
                    f"(Target HF: {HF_SAFE_TARGET}, Current HF: {engine.health_factor:.2f})"
                )
                
                # STEP 4: Open LP using ONLY the borrowed USD
                if borrowed_amount > MIN_POSITION_USD:
                    # Asymmetric LP range: tight floor, wide ceiling (-5% to +25%)
                    range_lower = current_price * 0.95
                    range_upper = current_price * 1.25
                    
                    lp_capital = min(borrowed_amount * 0.90, engine.usd_balance - GAS_RESERVE_USD)
                    
                    if lp_capital >= MIN_POSITION_USD:
                        engine.open_lp(
                            lp_capital,
                            range_lower,
                            range_upper,
                            current_price,
                            timestamp,
                            strategy="ACCUMULATOR_CONSERVATIVE_LP"
                        )
                        logger.info(
                            f"[{timestamp.date()}] STEP 4 - OPEN LP: Opened LP with ${lp_capital:.2f} "
                            f"(from borrowed funds) | Range: ${range_lower:.2f} - ${range_upper:.2f}. "
                            f"Remaining balance: ${engine.usd_balance:.2f}"
                        )
            else:
                logger.warning(
                    f"[{timestamp.date()}] Cannot borrow safely. Current HF: {engine.health_factor:.2f} "
                    f"(need >= {HF_SAFE_TARGET}). Skipping borrow step. Only holding BTC collateral."
                )
    
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
        
        # Calculate target amount (20% of safe balance)
        target_amount = safe_balance * 0.20
        
        # Validate minimum position size
        if target_amount < MIN_POSITION_USD:
            logger.debug(
                f"[{timestamp.date()}] Capital insuficiente para dip buy. "
                f"Target: ${target_amount:.2f} < Min: ${MIN_POSITION_USD:.2f}. Ignorando entrada."
            )
            return
        
        # Never exceed safe balance (no forced buys)
        dip_buy_amount = min(target_amount, safe_balance)
        
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
        entry_signal: dict,
        amount_pct: float = 0.40
    ) -> None:
        """
        Bull Mode Entry: Aggressive DeFi strategy to accumulate BTC and farm yields.
        
        CRITICAL DeFi FLOW:
        1. Buy Spot BTC using safe balance
        2. Add BTC as collateral to AAVE
        3. Borrow USD respecting HF_SAFE_TARGET (max 2.0)
        4. Open multiple LPs using ONLY borrowed USD (never use Spot cash for LP)
        
        This maximizes leverage while protecting the core BTC position.
        
        Args:
            entry_signal: Dict with 'type' (MOMENTUM/DIP) and 'reason'
            amount_pct: Percentage of safe balance to allocate for buying BTC
        """
        entry_type = entry_signal.get('type', 'UNKNOWN')
        entry_reason = entry_signal.get('reason', 'No reason provided')
        
        logger.info(
            f"[{timestamp.date()}] 🚀 BULL ENTRY ({entry_type}): {entry_reason}. "
            f"Unleashing DeFi Power with {amount_pct:.0%} allocation! Spot → Collateral → Borrow → LP"
        )
        
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        # Calculate allocations based on agent recommendation
        total_allocation = safe_balance * amount_pct
        
        # Validate minimum capital
        if total_allocation < MIN_POSITION_USD:
            logger.debug(
                f"[{timestamp.date()}] Capital insuficiente para bull entry. "
                f"Target: ${total_allocation:.2f} < Min: ${MIN_POSITION_USD:.2f}. Ignorando entrada."
            )
            return
        
        # Never exceed safe balance (no forced positions)
        total_allocation = min(total_allocation, safe_balance)
        
        # ===== STEP 1: Build Spot BTC position =====
        spot_allocation = total_allocation * 0.40  # 40% of allocated for spot buying
        
        if spot_allocation >= MIN_POSITION_USD:
            spot_allocation = min(spot_allocation, engine.usd_balance - GAS_RESERVE_USD)
            engine.buy_and_hodl(spot_allocation, current_price, timestamp)
            logger.info(
                f"[{timestamp.date()}] STEP 1 - SPOT BUY: Bought BTC with ${spot_allocation:.2f}. "
                f"New BTC position: {engine.btc_hodl_balance:.6f} BTC"
            )
        
        # ===== STEP 2: Add BTC as collateral to AAVE =====
        if engine.btc_hodl_balance > 0:
            engine.add_collateral(engine.btc_hodl_balance)
            logger.info(
                f"[{timestamp.date()}] STEP 2 - ADD COLLATERAL: Sent {engine.btc_hodl_balance:.6f} BTC "
                f"(${engine.btc_hodl_balance * current_price:.2f}) to AAVE as collateral"
            )
        
        # ===== STEP 3: Calculate and execute safe borrow respecting HF_SAFE_TARGET =====
        collateral_value = engine.btc_hodl_balance * current_price
        current_debt = engine.total_debt_usd
        
        if collateral_value > 0 and engine.health_factor >= HF_SAFE_TARGET:
            # Max borrow = (collateral * 0.80 / HF_SAFE_TARGET) - current_debt
            # CRITICAL FIX: Calculate borrow respecting existing debt to avoid HF breakage
            max_safe_debt = (collateral_value * 0.80) / HF_SAFE_TARGET
            borrow_amount = max(0.0, max_safe_debt - current_debt)
            
            if borrow_amount > MIN_POSITION_USD:
                borrowed_amount = engine.borrow_funds(borrow_amount, current_price)
                logger.info(
                    f"[{timestamp.date()}] STEP 3 - BORROW: Borrowed ${borrowed_amount:.2f} USD "
                    f"(Max safe debt: ${max_safe_debt:.2f}, Existing debt: ${current_debt:.2f}, Target HF: {HF_SAFE_TARGET})"
                )
                
                # ===== STEP 4: Open LPs using ONLY the borrowed USD =====
                if borrowed_amount > MIN_POSITION_USD:
                    # Allocate borrowed funds across multiple LPs for diversification
                    lp1_capital = borrowed_amount * 0.50  # 50% into first LP
                    lp2_capital = borrowed_amount * 0.40  # 40% into second LP (staggered range)
                    
                    # First LP: tight floor, wide ceiling (-5% to +25%)
                    range_lower_1 = current_price * 0.95
                    range_upper_1 = current_price * 1.25
                    
                    lp1_capital = min(lp1_capital, engine.usd_balance - GAS_RESERVE_USD)
                    if lp1_capital >= MIN_POSITION_USD:
                        engine.open_lp(
                            lp1_capital,
                            range_lower_1,
                            range_upper_1,
                            current_price,
                            timestamp,
                            strategy="ACCUMULATOR_BULL_LP_1"
                        )
                        logger.info(
                            f"[{timestamp.date()}] STEP 4a - OPEN LP #1: ${lp1_capital:.2f} "
                            f"| Range: ${range_lower_1:.2f} - ${range_upper_1:.2f}. "
                            f"Remaining balance: ${engine.usd_balance:.2f}"
                        )
                    
                    # Second LP: more aggressive range (-2% to +35%)
                    range_lower_2 = current_price * 0.98
                    range_upper_2 = current_price * 1.35
                    
                    lp2_capital = min(lp2_capital, engine.usd_balance - GAS_RESERVE_USD)
                    if lp2_capital >= MIN_POSITION_USD:
                        engine.open_lp(
                            lp2_capital,
                            range_lower_2,
                            range_upper_2,
                            current_price,
                            timestamp,
                            strategy="ACCUMULATOR_BULL_LP_2"
                        )
                        logger.info(
                            f"[{timestamp.date()}] STEP 4b - OPEN LP #2: ${lp2_capital:.2f} "
                            f"| Range: ${range_lower_2:.2f} - ${range_upper_2:.2f}. "
                            f"Remaining balance: ${engine.usd_balance:.2f}"
                        )
        else:
            logger.warning(
                f"[{timestamp.date()}] Cannot borrow safely. Current HF: {engine.health_factor:.2f} "
                f"(need >= {HF_SAFE_TARGET}). Skipping borrow step. Holding BTC collateral only."
            )
    
    def _maintain_positions(
        self, 
        engine: 'TradingEngine', 
        current_price: float, 
        timestamp: pd.Timestamp
    ) -> None:
        """
        Maintain existing LP positions: ONLY close if EMERGENCY (HF < HF_CRITICAL).
        
        Protection of Capital:
        - OUT-OF-RANGE LPs are NOT closed automatically
        - Only close if Health Factor drops below HF_CRITICAL (1.3)
        - This prevents losses and allows LPs to recover when price re-enters range
        """
        lps_to_close = []
        
        # EMERGENCY CHECK: Only close LPs if Health Factor is critically low
        if engine.health_factor < HF_CRITICAL:
            logger.warning(
                f"[{timestamp.date()}] 🚨 HEALTH FACTOR CRITICAL: {engine.health_factor:.2f} < {HF_CRITICAL}. "
                f"Closing LPs to reduce debt and improve HF."
            )
            # Mark ALL LPs for emergency closure
            for lp in engine.active_lps:
                lps_to_close.append(lp['id'])
        else:
            # Normal mode: Track out-of-range duration (informational only, do NOT close)
            for lp in engine.active_lps:
                is_out_of_range = current_price > lp['range_upper'] or current_price < lp['range_lower']
                if is_out_of_range:
                    last_date = lp.get('last_out_of_range_date')
                    if last_date != timestamp.date():
                        lp['days_out_of_range'] = lp.get('days_out_of_range', 0) + 1
                        lp['last_out_of_range_date'] = timestamp.date()
                    
                    logger.debug(
                        f"[{timestamp.date()}] LP {lp['id']} out of range for {lp.get('days_out_of_range', 0)} days. "
                        f"Price ${current_price:.2f} vs Range [${lp['range_lower']:.2f}, ${lp['range_upper']:.2f}]. "
                        f"Monitoring (NOT closing - protection against forced losses)"
                    )
                else:
                    lp['days_out_of_range'] = 0
                    lp['last_out_of_range_date'] = None
        
        # Close marked LPs only in emergency
        for lp_id in lps_to_close:
            logger.warning(f"[{timestamp.date()}] Emergency closing LP {lp_id} to restore health factor.")
            engine.close_lp(lp_id, current_price, timestamp, is_emergency=True)
