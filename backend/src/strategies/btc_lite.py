"""
BTC Lite Strategy (V7 - BTC Standard Lite).

Strategy that uses ML predictions to make leveraged trading decisions:
- prediction == 1 (BULLISH): Leverage existing collateral + amplify
- prediction == 0 (NEUTRAL): Hold BTC, convert excess USD to BTC
"""
import pandas as pd
import logging
from typing import TYPE_CHECKING

from .base import BaseStrategy
from ..core import LOAN_TO_VALUE_RATIO
from ..ai import analyze_market_regime
from ..config import (
    GAS_RESERVE_USD, MIN_LIQUID_BUFFER, SIMULATED_GAS_FEE_USD,
    HF_REFINANCE_THRESHOLD, SAFE_HF_AFTER_BORROW, MAX_ACTIVE_LPS, ENTRY_SIZE_PCT,
    ATR_MULTIPLIER_BULLISH_LOWER, ATR_MULTIPLIER_BULLISH_UPPER, ATR_MULTIPLIER_NEUTRAL
)
from ..utils.math import calculate_safe_borrow_amount, calculate_entry_size, calculate_dynamic_range, calculate_directional_range

if TYPE_CHECKING:
    from ..core import TradingEngine

logger = logging.getLogger(__name__)

# Strategy constants
DAYS_OUT_OF_RANGE_THRESHOLD = 10


class BTCLiteStrategy(BaseStrategy):
    """
    BTC Standard Lite Strategy (V7).
    
    ML-driven strategy that:
    - Uses model predictions to determine market regime (BULLISH vs NEUTRAL)
    - BULLISH: Leverage collateral and amplify with borrowed capital
    - NEUTRAL: Convert excess USD to BTC HODL (no leverage)
    - Multi-pool scaling with dynamic position sizing
    - Smart debt repayment in neutral periods
    """
    
    def execute(self, row: pd.Series, engine: 'TradingEngine', timestamp: pd.Timestamp) -> None:
        """
        Execute the BTC Lite strategy for a single time step.
        
        Args:
            row: Current market data with indicators and predictions
            engine: TradingEngine instance with portfolio state
            timestamp: Current timestamp
        """
        current_price = row['Close']
        
        # --- 1. CLOSING LOGIC: Close out-of-range LPs ---
        self._handle_lp_closures(engine, current_price, timestamp)
        
        # --- 2. OPENING LOGIC: Determine regime and execute ---
        prediction = self._get_prediction(row)
        
        if engine.total_debt_usd == 0:
            # STATE 1: Pre-Leverage (waiting for BULLISH signal)
            self._handle_pre_leverage_state(row, engine, timestamp, current_price, prediction)
        else:
            # STATE 2: Post-Leverage (already leveraged and operating)
            self._handle_post_leverage_state(row, engine, timestamp, current_price, prediction)
    
    def _handle_lp_closures(self, engine: 'TradingEngine', current_price: float, timestamp: pd.Timestamp) -> None:
        """Close LPs that have been out of range for too long."""
        if engine.active_lps:
            for lp in engine.active_lps.copy():
                if lp['days_out_of_range'] > DAYS_OUT_OF_RANGE_THRESHOLD:
                    engine.close_lp(lp_id=lp['id'], current_btc_price=current_price, timestamp=timestamp)
    
    def _get_prediction(self, row: pd.Series) -> int:
        """
        Get market prediction from ML model or fallback to regime analyzer.
        
        Returns:
            1 = BULLISH (predicted upward move)
            0 = NEUTRAL (predicted stability/downward)
        """
        prediction = row.get('prediction', None)
        if prediction is None:
            # Backward-compatibility: use legacy regime analyzer
            regime = analyze_market_regime(row)
            prediction = 1 if regime == 'BULLISH' else 0
        return prediction
    
    def _handle_pre_leverage_state(
        self, 
        row: pd.Series, 
        engine: 'TradingEngine', 
        timestamp: pd.Timestamp,
        current_price: float,
        prediction: int
    ) -> None:
        """
        Handle trading logic when no leverage is deployed (total_debt_usd == 0).
        
        BULLISH: Buy BTC collateral and leverage it with borrowing
        NEUTRAL: Convert excess USD to BTC HODL
        """
        if prediction == 1:  # BULLISH
            self._execute_bullish_entry(row, engine, timestamp, current_price)
        else:  # NEUTRAL
            self._execute_neutral_hodl(engine, timestamp, current_price)
    
    def _execute_bullish_entry(
        self,
        row: pd.Series,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float
    ) -> None:
        """
        Execute BULLISH entry: leverage existing or new collateral.
        
        Steps:
        1. Calculate dynamic position size
        2. Buy BTC collateral (if needed)
        3. Borrow against collateral
        4. Execute recursive loop (50% to collateral, 50% to LP)
        """
        # V4: Calculate position size based on market conditions
        ath_price = row.get('ATH_52w', current_price * 1.5)
        fng_value = row.get('FNG_Value', 50)
        
        allocation_pct = calculate_entry_size(engine.usd_balance, current_price, ath_price, fng_value)
        capital_to_allocate = engine.usd_balance * allocation_pct
        
        # Ensure we keep minimum liquid buffer
        liquid_minimum = engine.usd_balance * MIN_LIQUID_BUFFER
        capital_to_allocate = min(capital_to_allocate, engine.usd_balance - liquid_minimum)
        
        # Subtract estimated gas costs for this entry (buy + open LP)
        estimated_gas_costs = SIMULATED_GAS_FEE_USD * 2
        capital_to_allocate = max(0.0, capital_to_allocate - estimated_gas_costs)
        
        if capital_to_allocate < 10:
            logger.debug(
                f"[{timestamp.date()}] Sinal BULLISH, mas capital insuficiente para alavancagem "
                f"(Alocável: ${capital_to_allocate:.2f}, Mínimo Líquido: ${liquid_minimum:.2f})"
            )
            return
        
        logger.info(
            f"[{timestamp.date()}] PRIMEIRA POSIÇÃO 'BULLISH' (V7 BTC Standard). "
            f"Alocação: {allocation_pct:.0%} | Capital: ${capital_to_allocate:.2f} @ ${current_price:.2f} "
            f"| Mantendo líquido: ${engine.usd_balance - capital_to_allocate:.2f}"
        )
        
        # 1. Check if we already hold BTC (from previous NEUTRAL periods)
        if engine.btc_hodl_balance > 0.0001:
            logger.info(
                f"[{timestamp.date()}] BULLISH: Leverage existing BTC collateral ({engine.btc_hodl_balance:.6f} BTC). "
                f"Skipping buy, proceeding to amplify via borrowing."
            )
        else:
            # No existing BTC: Buy new collateral with allocation
            engine.buy_and_hodl(capital_to_allocate, current_price)
            logger.info(f"[{timestamp.date()}] BULLISH: No existing BTC. Buying {capital_to_allocate/current_price:.6f} BTC as collateral.")
        
        # 2. Borrow against collateral (with HF guardrail)
        self._execute_safe_borrow(engine, timestamp, current_price)
        
        # 3. Execute recursive loop: 50% to collateral, 50% to LP
        self._execute_recursive_loop(row, engine, timestamp, current_price)
    
    def _execute_safe_borrow(
        self,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float
    ) -> None:
        """
        Safely borrow against collateral with HF simulation and scaling.
        """
        collateral_value = engine.btc_hodl_balance * current_price
        max_borrowable = collateral_value * LOAN_TO_VALUE_RATIO
        logger.debug(f"[{timestamp.date()}] BULLISH: Collateral = {engine.btc_hodl_balance:.6f} BTC @ ${current_price:.2f} = ${collateral_value:.2f}")
        
        # Apply scaling: only borrow a fraction of available borrowing power
        amount_to_borrow = max_borrowable * ENTRY_SIZE_PCT
        logger.debug(f"[{timestamp.date()}] Scaling: Max borrowable ${max_borrowable:.2f} → Scaled to ${amount_to_borrow:.2f} ({ENTRY_SIZE_PCT:.0%})")
        
        # Simulate HF after borrow
        projected_debt = engine.total_debt_usd + amount_to_borrow
        projected_hf = (collateral_value * 0.8) / projected_debt if projected_debt > 0 else 999.0
        
        # If projected HF falls below safety threshold, adjust the borrow amount
        if projected_hf < SAFE_HF_AFTER_BORROW:
            # Recalculate safe borrow to maintain target HF
            safe_amount = calculate_safe_borrow_amount(
                collateral_value,
                engine.total_debt_usd,
                SAFE_HF_AFTER_BORROW,
                min_borrow=10.0
            )
            # Take the smaller of scaled amount or safe amount
            amount_to_borrow = min(amount_to_borrow, safe_amount)
            if amount_to_borrow > 0:
                logger.debug(
                    f"[{timestamp.date()}] HF Guardrail: Adjusted borrow to ${amount_to_borrow:.2f} "
                    f"(projected HF would be {projected_hf:.2f}, target {SAFE_HF_AFTER_BORROW})"
                )
            else:
                logger.debug(
                    f"[{timestamp.date()}] HF Guardrail: Cannot borrow safely; would drop HF below {SAFE_HF_AFTER_BORROW}"
                )
                amount_to_borrow = 0.0
        
        if amount_to_borrow > 0:
            engine.total_debt_usd += amount_to_borrow
            engine.usd_balance += amount_to_borrow
            logger.info(f"[{timestamp.date()}] Empréstimo refinanciado: ${amount_to_borrow:.2f} (Projected HF: {projected_hf:.2f})")
        else:
            logger.info(f"[{timestamp.date()}] Empréstimo negado por guardrail de HF (Projected HF: {projected_hf:.2f} < {SAFE_HF_AFTER_BORROW})")
    
    def _execute_recursive_loop(
        self,
        row: pd.Series,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float
    ) -> None:
        """
        Execute recursive loop: use borrowed funds for 50% collateral, 50% LP.
        V3: Uses ATR for dynamic range calculation.
        """
        collateral_value = engine.btc_hodl_balance * current_price
        hf = (collateral_value * 0.80) / engine.total_debt_usd if engine.total_debt_usd > 0 else 999.0
        
        # Base safe balance excludes the absolute gas reserve
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        if hf > HF_REFINANCE_THRESHOLD:
            # SAFE: Use the entire safe balance (reserve preserved)
            available_for_loop = safe_balance
            logger.debug(f"[{timestamp.date()}] HF={hf:.2f} > {HF_REFINANCE_THRESHOLD}: Usando alavancagem (refinanciamento) sobre safe_balance=${safe_balance:.2f}")
        else:
            # CAREFUL: Use a conservative portion of the safe balance
            available_for_loop = safe_balance - (safe_balance * MIN_LIQUID_BUFFER)
            logger.debug(f"[{timestamp.date()}] HF={hf:.2f} <= {HF_REFINANCE_THRESHOLD}: Usando cash conservadoramente sobre safe_balance=${safe_balance:.2f}")
        
        # Guard against negative available
        available_for_loop = max(0.0, available_for_loop)
        
        btc_bought = available_for_loop / current_price if current_price > 0 else 0.0
        btc_to_collateral = btc_bought * 0.50
        btc_to_lp = btc_bought * 0.50
        
        # 4. Add to collateral
        capital_for_collateral_usd = btc_to_collateral * current_price
        if capital_for_collateral_usd > 1:
            engine.add_collateral(btc_to_collateral)
            engine.usd_balance -= capital_for_collateral_usd
            logger.info(f"[{timestamp.date()}] Loop: {btc_to_collateral:.6f} BTC adicionado ao colateral.")
        
        # 5. Open LP with directional ranges (V7 - Target Selling)
        safe_balance_after = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        capital_for_lp_usd = max(0.0, safe_balance_after - (safe_balance_after * MIN_LIQUID_BUFFER))
        if capital_for_lp_usd > 1:
            # V7: Use directional range for profit-taking
            atr = row.get('ATR', 0.0)
            range_lower, range_upper = calculate_directional_range(current_price, atr, target_multiplier=15.0)
            logger.info(
                f"[{timestamp.date()}] Loop: Abrindo LP Directional (ATR={atr:.2f}) com ${capital_for_lp_usd:.2f} "
                f"(Range: ${range_lower:.2f}-${range_upper:.2f}) - Target Selling"
            )
            
            engine.open_lp(capital_for_lp_usd, range_lower, range_upper, current_price, timestamp, strategy="BULLISH_ML_DIRECTIONAL_V7")
            engine.usd_balance -= capital_for_lp_usd
        else:
            logger.debug(f"[{timestamp.date()}] Loop: Insuficiente para LP após buffer líquido.")
    
    def _execute_neutral_hodl(
        self,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float
    ) -> None:
        """
        Execute NEUTRAL strategy: convert excess USD to BTC HODL.
        """
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        liquid_minimum = safe_balance * MIN_LIQUID_BUFFER
        excess_usd = max(0.0, safe_balance - liquid_minimum)
        
        # Minimum trade size to prevent spam
        if excess_usd < 50.0:
            logger.debug(f"[{timestamp.date()}] NEUTRAL: Trade size too small (${excess_usd:.2f} < $50.00). Skipping.")
            return
        
        if excess_usd > 10:  # Only buy if we have meaningful capital
            btc_to_buy = excess_usd / current_price if current_price > 0 else 0.0
            if btc_to_buy > 0.0001:  # Minimum viable BTC amount
                engine.buy_and_hodl(excess_usd, current_price)
                logger.info(
                    f"[{timestamp.date()}] NEUTRAL (BTC Standard Lite): Convertendo ${excess_usd:.2f} USD → {btc_to_buy:.6f} BTC HODL. "
                    f"Mantendo líquido: ${liquid_minimum:.2f}"
                )
            else:
                logger.debug(f"[{timestamp.date()}] NEUTRAL: Saldo insuficiente para compra de BTC (${excess_usd:.2f}).")
        else:
            logger.debug(f"[{timestamp.date()}] NEUTRAL: Já em BTC HODL ou reserva insuficiente (Excesso: ${excess_usd:.2f}).")
    
    def _handle_post_leverage_state(
        self,
        row: pd.Series,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float,
        prediction: int
    ) -> None:
        """
        Handle trading logic when leverage is already deployed (total_debt_usd > 0).
        
        Allow opening additional LPs up to MAX_ACTIVE_LPS (multi-pool scaling).
        """
        if len(engine.active_lps) >= MAX_ACTIVE_LPS:
            return  # Already at max LPs
        
        # V4 Dynamic Allocation for post-leverage state
        ath_price = row.get('ATH_52w', current_price * 1.5)
        fng_value = row.get('FNG_Value', 50)
        
        # Respect absolute gas reserve before allocating
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        # Each new entry should use a fixed fraction of the safe balance
        capital_to_allocate = safe_balance * ENTRY_SIZE_PCT
        
        # Also ensure we keep minimum liquid buffer and gas for txs
        liquid_minimum = engine.usd_balance * MIN_LIQUID_BUFFER
        estimated_gas_costs = SIMULATED_GAS_FEE_USD * 2
        max_allowable = max(0.0, engine.usd_balance - liquid_minimum - estimated_gas_costs - GAS_RESERVE_USD)
        capital_to_allocate = min(capital_to_allocate, max_allowable)
        
        if capital_to_allocate <= 10:
            logger.debug(
                f"[{timestamp.date()}] Saldo insuficiente para novo LP (Alocável: ${capital_to_allocate:.2f}, "
                f"Mínimo Líquido: ${liquid_minimum:.2f})"
            )
            return
        
        # Check Health Factor for margin reuse decision
        collateral_value = engine.btc_hodl_balance * current_price
        hf = (collateral_value * 0.80) / engine.total_debt_usd if engine.total_debt_usd > 0 else 999.0
        
        if prediction == 1:  # BULLISH
            self._execute_post_leverage_bullish(row, engine, timestamp, current_price, hf, capital_to_allocate)
        elif prediction == 0:  # NEUTRAL
            self._execute_post_leverage_neutral(row, engine, timestamp, current_price, hf, capital_to_allocate)
        else:
            logger.warning(f"[{timestamp.date()}] Unknown prediction value: {prediction}")
    
    def _execute_post_leverage_bullish(
        self,
        row: pd.Series,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float,
        hf: float,
        capital_to_allocate: float
    ) -> None:
        """
        Execute BULLISH post-leverage: ladder LP ranges and potentially refinance.
        V3: Uses ATR for dynamic range calculation with ladder adjustment.
        """
        # V7: Directional ranges with ladder adjustment for multiple LPs
        atr = row.get('ATR', 0.0)
        index = len(engine.active_lps)
        
        # Use directional range with ladder adjustment (reduce target multiplier for each additional LP)
        base_target = 15.0
        target_multiplier = max(8.0, base_target - (2.0 * index))  # Ladder down: 15, 13, 11, 9...
        range_lower, range_upper = calculate_directional_range(current_price, atr, target_multiplier)
        strategy_name = "BULLISH_ML_DIRECTIONAL_V7"
        
        if hf > HF_REFINANCE_THRESHOLD:
            # PRE-BORROW HF SIMULATION: Calculate safe borrow amount with scaling
            collateral_value = engine.btc_hodl_balance * current_price
            safe_borrow = calculate_safe_borrow_amount(
                collateral_value,
                engine.total_debt_usd,
                SAFE_HF_AFTER_BORROW,
                min_borrow=10.0
            )
            
            if safe_borrow > 0:
                # Apply scaling: only borrow a fraction of safe borrowing power
                scaled_borrow = safe_borrow * ENTRY_SIZE_PCT
                # Cap at what we wanted to allocate
                amount_to_borrow = min(scaled_borrow, capital_to_allocate)
                engine.total_debt_usd += amount_to_borrow
                engine.usd_balance += amount_to_borrow
                logger.info(
                    f"[{timestamp.date()}] HF={hf:.2f} > {HF_REFINANCE_THRESHOLD}: Scaled Refinancing "
                    f"(${amount_to_borrow:.2f} of ${safe_borrow:.2f} available, {ENTRY_SIZE_PCT:.0%} scaling)"
                )
                capital_to_allocate = amount_to_borrow
            else:
                logger.debug(
                    f"[{timestamp.date()}] HF Guardrail: Cannot borrow despite HF={hf:.2f} (would breach {SAFE_HF_AFTER_BORROW})"
                )
        
        logger.info(
            f"[{timestamp.date()}] BULLISH (V6): LP Range Amplo ${capital_to_allocate:.2f} | "
            f"HF={hf:.2f} | Líquido: ${engine.usd_balance - capital_to_allocate:.2f} "
            f"(Range: ${range_lower:.2f}-${range_upper:.2f})"
        )
        
        # Open LP
        if capital_to_allocate > 0 and len(engine.active_lps) < MAX_ACTIVE_LPS:
            engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp, strategy=strategy_name)
            engine.usd_balance -= capital_to_allocate
    
    def _execute_post_leverage_neutral(
        self,
        row: pd.Series,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float,
        hf: float,
        capital_to_allocate: float
    ) -> None:
        """
        Execute NEUTRAL post-leverage: farm fees conservatively and smart repay debt.
        V3: Uses ATR for dynamic symmetric range calculation.
        """
        # Smart Repay: Use excess cash to pay down debt
        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        buffer_needed = safe_balance * MIN_LIQUID_BUFFER
        excess_cash = max(0.0, safe_balance - buffer_needed)
        
        if excess_cash > 20.0 and engine.total_debt_usd > 0:
            if engine.usd_balance > SIMULATED_GAS_FEE_USD:
                # Pay down up to the excess_cash, but never more than outstanding debt
                payment_amount = min(excess_cash, engine.total_debt_usd)
                engine.total_debt_usd = max(0.0, engine.total_debt_usd - payment_amount)
                engine.usd_balance -= (payment_amount + SIMULATED_GAS_FEE_USD)
                logger.info(
                    f"[{timestamp.date()}] SMART REPAY: Using excess cash to pay down debt. "
                    f"Paid: ${payment_amount:.2f}, New Debt: ${engine.total_debt_usd:.2f}."
                )
                # Recompute capital_to_allocate after repayment
                safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
                capital_to_allocate = safe_balance * ENTRY_SIZE_PCT
                liquid_minimum = engine.usd_balance * MIN_LIQUID_BUFFER
                estimated_gas_costs = SIMULATED_GAS_FEE_USD * 2
                max_allowable = max(0.0, engine.usd_balance - liquid_minimum - estimated_gas_costs - GAS_RESERVE_USD)
                capital_to_allocate = min(capital_to_allocate, max_allowable)
        
        if capital_to_allocate <= 0:
            logger.info(
                f"[{timestamp.date()}] NEUTRAL (V7 BTC Standard): Leverage already deployed. "
                f"HF={hf:.2f} (Target: {HF_REFINANCE_THRESHOLD}). "
                f"Holding collateral & farming fees to service debt."
            )
            return
        
        # V3: Conservative farming with ATR-based symmetric ranges
        atr = row.get('ATR', 0.0)
        if atr > 0:
            # Use symmetric ATR multiplier for neutral positions
            range_lower, range_upper = calculate_dynamic_range(
                current_price, atr,
                ATR_MULTIPLIER_NEUTRAL,
                ATR_MULTIPLIER_NEUTRAL
            )
            strategy_name = "NEUTRAL_ML_ATR_V3"
        else:
            # Fallback to percentage-based
            range_lower = current_price * 0.70
            range_upper = current_price * 1.60
            strategy_name = "NEUTRAL_ML_DYNAMIC_V7"
        
        logger.info(
            f"[{timestamp.date()}] NEUTRAL (V7 BTC Standard): Conservative LP Farm ${capital_to_allocate:.2f} | "
            f"HF={hf:.2f} | Líquido: ${engine.usd_balance - capital_to_allocate:.2f} "
            f"(Range: ${range_lower:.2f}-${range_upper:.2f})"
        )
        
        # Open LP
        if capital_to_allocate > 0 and len(engine.active_lps) < MAX_ACTIVE_LPS:
            engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp, strategy=strategy_name)
            engine.usd_balance -= capital_to_allocate
