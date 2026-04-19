"""
BTC Lite Strategy (V13 - Smart Reserve).

[Estratégia Principal (Main)]
Objetivo: USD (Maximizar retorno absoluto em dólar)
Regime Ideal: Bull / Sideways
Risco Esperado: Médio/Alto (Exposição direcional e alavancagem dinâmica)

Strategy that uses ML predictions to make leveraged trading decisions:
- prediction == 1 (BULLISH): Leverage existing collateral + amplify
- prediction == 0 (NEUTRAL): Hold BTC (60% HODL + 40% LP), keep 20% USD Reserve

V13 Improvements (Smart Reserve):
- Heavy BTC Neutral State: 60% HODL + 40% LP (instead of 100% LP)
- Covered Borrow: Limit debt to 3x cash reserve (prevents naked leverage)
- Smart Deleveraging: Use USD reserve to pay debt if HF < 1.6 (prevents forced LP closures)
"""
import pandas as pd
import logging
from typing import TYPE_CHECKING

from .base import BaseStrategy
from backend.src.core import LOAN_TO_VALUE_RATIO
from backend.src.ai import analyze_market_regime
from backend.src.config import (
    GAS_RESERVE_USD, MIN_LIQUID_BUFFER,
    HF_REFINANCE_THRESHOLD, SAFE_HF_AFTER_BORROW, MAX_ACTIVE_LPS, ENTRY_SIZE_PCT,
    ATR_MULTIPLIER_BULLISH_LOWER, ATR_MULTIPLIER_BULLISH_UPPER, ATR_MULTIPLIER_NEUTRAL,
    TARGET_RESERVE_RATIO, MIN_HARVEST_USD, MAX_DEBT_RATIO,
    MAX_DEBT_TO_RESERVE_RATIO, DELEVERAGE_THRESHOLD_HF
)
from backend.src.utils.math import calculate_safe_borrow_amount, calculate_entry_size, calculate_dynamic_range, calculate_directional_range

if TYPE_CHECKING:
    from backend.src.core import TradingEngine

logger = logging.getLogger(__name__)

# Strategy constants
DAYS_OUT_OF_RANGE_THRESHOLD = 10


class BTCLiteStrategy(BaseStrategy):
    """
    BTC Standard Lite Strategy (V13 - Smart Reserve).
    
    ML-driven strategy that:
    - Uses model predictions to determine market regime (BULLISH vs NEUTRAL)
    - BULLISH: Leverage collateral and amplify with borrowed capital
    - NEUTRAL: Heavy BTC exposure (60% HODL + 40% LP), maintain 20% USD Reserve
    - Smart Deleveraging: Use reserve cash to defend HF before closing LPs
    - Covered Borrow: Limit debt to 3x cash reserve
    - Multi-pool scaling with dynamic position sizing
    - Automatic take-profit when LPs hit upper target
    """

    def _calculate_equity_snapshot(self, engine: 'TradingEngine', current_price: float) -> tuple:
        lp_total_value = 0.0
        for lp in engine.active_lps:
            asset_value, _, _ = engine._get_lp_value(lp, current_price)
            lp_total_value += float(asset_value)
            lp_total_value += lp['fees_accrued_usdt'] + (lp['fees_accrued_btc'] * current_price)

        equity = (engine.btc_hodl_balance * current_price) + lp_total_value + engine.usd_balance - engine.total_debt_usd
        target_reserve = equity * TARGET_RESERVE_RATIO
        usd_surplus = engine.usd_balance - target_reserve
        return equity, target_reserve, usd_surplus

    def _calculate_total_fees_usd(self, engine: 'TradingEngine', current_price: float) -> float:
        fees_total = 0.0
        for lp in engine.active_lps:
            fees_total += lp['fees_accrued_usdt'] + (lp['fees_accrued_btc'] * current_price)
        return fees_total

    def _process_profit_routing(self, engine: 'TradingEngine', equity: float, current_price: float) -> float:
        target_reserve = equity * TARGET_RESERVE_RATIO
        usd_surplus = engine.usd_balance - target_reserve

        if usd_surplus > 10:
            is_bearish = getattr(self, "_latest_prediction", 0) == -1
            if not is_bearish:
                engine.buy_and_hodl(usd_surplus, current_price)
                logger.info(
                    f"FLYWHEEL: Reserve Full. Converted ${usd_surplus:.2f} profit to BTC."
                )
        elif usd_surplus < -0.20 * target_reserve:
            # Only log if deficit is critical (> 20% of target reserve)
            logger.info(
                f"FLYWHEEL: Critical Reserve Deficit. Target=${target_reserve:.2f}, Current=${engine.usd_balance:.2f}."
            )

        return usd_surplus
    
    def execute(self, row: pd.Series, engine: 'TradingEngine', timestamp: pd.Timestamp) -> dict:
        """
        Execute the BTC Lite strategy for a single time step.
        
        Args:
            row: Current market data with indicators and predictions
            engine: TradingEngine instance with portfolio state
            timestamp: Current timestamp
            
        Returns:
            dict: Standardized decision dictionary
        """
        decision = {"action": "HOLD", "sizing": 0.0, "reason": "No clear signal", "expected_risk": "Med"}
        current_price = row['Close']
        
        # Flywheel equity snapshot
        equity, target_reserve, usd_surplus = self._calculate_equity_snapshot(engine, current_price)

        # --- 0. SMART DELEVERAGING: Check if we need to defend HF with cash reserve ---
        if engine.total_debt_usd > 0:
            self._handle_smart_deleveraging(engine, current_price, timestamp)
            decision.update({"action": "DELEVERAGE_CHECK", "sizing": 1.0, "reason": "Deleveraging pass", "expected_risk": "Low"})
        
        # --- 1. CLOSING LOGIC: Close out-of-range LPs ---
        self._handle_lp_closures(engine, current_price, timestamp)

        # Refresh equity snapshot after defensive actions
        equity, target_reserve, usd_surplus = self._calculate_equity_snapshot(engine, current_price)
        
        # --- 2. Determine regime and harvest lazily ---
        prediction = self._get_prediction(row)
        self._latest_prediction = prediction

        accrued_fees = self._calculate_total_fees_usd(engine, current_price)
        if accrued_fees > MIN_HARVEST_USD or usd_surplus < -100:
            try:
                engine._check_and_harvest(current_price, timestamp)
            except Exception as e:
                logger.exception("Erro durante smart harvest condicional: %s", e)
            equity, target_reserve, usd_surplus = self._calculate_equity_snapshot(engine, current_price)

        # --- 3. Profit routing (Flywheel) ---
        usd_surplus = self._process_profit_routing(engine, equity, current_price)

        # Refresh snapshot after routing conversions
        equity, target_reserve, usd_surplus = self._calculate_equity_snapshot(engine, current_price)
        
        # --- 4. OPENING LOGIC: Determine regime and execute ---
        if engine.total_debt_usd == 0:
            # STATE 1: Pre-Leverage (waiting for BULLISH signal)
            self._handle_pre_leverage_state(row, engine, timestamp, current_price, prediction, target_reserve)
            decision.update({"action": "PRE_LEVERAGE_EXEC", "sizing": 1.0, "reason": f"Pred: {prediction}", "expected_risk": "Med"})
        else:
            # STATE 2: Post-Leverage (already leveraged and operating)
            self._handle_post_leverage_state(row, engine, timestamp, current_price, prediction, target_reserve)
            decision.update({"action": "POST_LEVERAGE_EXEC", "sizing": 1.0, "reason": f"Pred: {prediction}", "expected_risk": "High"})
            
        return decision
    
    def _handle_smart_deleveraging(self, engine: 'TradingEngine', current_price: float, timestamp: pd.Timestamp) -> None:
        """
        V13 Smart Deleveraging: Use reserve cash to pay down debt if HF drops below threshold.
        Prevents forced LP closures during dips.
        """
        if engine.total_debt_usd == 0:
            return  # No debt to deleverage
        
        # Calculate Health Factor
        collateral_value = engine.btc_collateral_balance * current_price
        hf = (collateral_value * 0.80) / engine.total_debt_usd if engine.total_debt_usd > 0 else 999.0
        
        # Only deleverage if HF drops below threshold
        if hf >= DELEVERAGE_THRESHOLD_HF:
            return
        
        # Calculate available reserve cash (respect gas reserve)
        available_cash = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        
        if available_cash > 20.0:  # Minimum meaningful amount
            # Determine repayment amount: min of (available cash, total debt)
            payment_amount = min(available_cash, engine.total_debt_usd)
            
            # Execute repayment
            old_debt = engine.total_debt_usd
            old_hf = hf
            engine.total_debt_usd = max(0.0, engine.total_debt_usd - payment_amount)
            engine.usd_balance -= (payment_amount + engine.gas_fee_usd)
            
            # Recalculate improved HF
            new_hf = (collateral_value * 0.80) / engine.total_debt_usd if engine.total_debt_usd > 0 else 999.0
            
            logger.info(
                f"[{timestamp.date()}] 🛡️ DEFENSE (V13 Smart Reserve): Used Emergency Reserve to repay debt. "
                f"Paid: ${payment_amount:.2f} | Debt: ${old_debt:.2f} → ${engine.total_debt_usd:.2f} | "
                f"HF: {old_hf:.2f} → {new_hf:.2f}"
            )
    
    def _handle_lp_closures(self, engine: 'TradingEngine', current_price: float, timestamp: pd.Timestamp) -> None:
        """Close LPs that have been out of range for too long or hit take-profit target."""
        if engine.active_lps:
            for lp in engine.active_lps.copy():
                # V12: Take-Profit & Repay - Close LPs that hit upper target
                if current_price > lp['range_upper']:
                    logger.info(
                        f"[{timestamp.date()}] TAKE PROFIT: LP {lp['id']} out of range (High). "
                        f"Price ${current_price:.2f} > Upper ${lp['range_upper']:.2f}. Closing and repaying debt."
                    )
                    returned_capital = engine.close_lp(lp_id=lp['id'], current_btc_price=current_price, timestamp=timestamp)
                    
                    # Use returned capital to pay down debt
                    if engine.total_debt_usd > 0 and engine.usd_balance > engine.gas_fee_usd:
                        # Calculate available cash for repayment (keep gas reserve)
                        safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
                        buffer_needed = safe_balance * MIN_LIQUID_BUFFER
                        available_for_repay = max(0.0, safe_balance - buffer_needed)
                        
                        if available_for_repay > 20.0:
                            payment_amount = min(available_for_repay, engine.total_debt_usd)
                            engine.total_debt_usd = max(0.0, engine.total_debt_usd - payment_amount)
                            engine.usd_balance -= (payment_amount + engine.gas_fee_usd)
                            logger.info(
                                f"[{timestamp.date()}] TAKE PROFIT REPAY: Paid ${payment_amount:.2f} debt. "
                                f"Remaining Debt: ${engine.total_debt_usd:.2f}"
                            )
                    continue
                
                # Standard closure: Out of range for too long
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
        prediction: int,
        target_reserve: float
    ) -> None:
        """
        Handle trading logic when no leverage is deployed (total_debt_usd == 0).
        
        BULLISH: Buy BTC collateral and leverage it with borrowing
        NEUTRAL: Heavy BTC Neutral State (60% HODL + 40% LP, maintain 20% reserve)
        """
        if prediction == 1:  # BULLISH
            self._execute_bullish_entry(row, engine, timestamp, current_price, target_reserve)
        else:  # NEUTRAL
            self._execute_neutral_hodl(engine, timestamp, current_price, target_reserve, row)
    
    def _execute_bullish_entry(
        self,
        row: pd.Series,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float,
        target_reserve: float
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

        # Respect dynamic reserve when sizing entries
        capital_to_allocate = min(capital_to_allocate, max(0.0, engine.usd_balance - target_reserve))
        
        # Subtract estimated gas costs for this entry (buy + open LP)
        estimated_gas_costs = engine.gas_fee_usd * 2
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
            
        # 1.5 Move ALL BTC to collateral
        if engine.btc_hodl_balance > 0:
            engine.add_collateral(engine.btc_hodl_balance)
        
        # 2. Borrow against collateral (with HF guardrail)
        self._execute_safe_borrow(engine, timestamp, current_price)
        
        # 3. Execute recursive loop: 50% to collateral, 50% to LP
        self._execute_recursive_loop(row, engine, timestamp, current_price, target_reserve)
    
    def _execute_safe_borrow(
        self,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float
    ) -> None:
        """
        Safely borrow against collateral with HF simulation and scaling.
        V13: Added "Covered Borrow" constraint - limit debt to MAX_DEBT_TO_RESERVE_RATIO * cash reserve.
        """
        collateral_value = engine.btc_collateral_balance * current_price
        max_borrowable = collateral_value * LOAN_TO_VALUE_RATIO

        # V14: Cap total leverage at conservative LTV
        debt_cap = collateral_value * MAX_DEBT_RATIO
        max_borrowable = max(0.0, min(max_borrowable, debt_cap - engine.total_debt_usd))
        logger.debug(f"[{timestamp.date()}] BULLISH: Collateral = {engine.btc_collateral_balance:.6f} BTC @ ${current_price:.2f} = ${collateral_value:.2f}")
        
        # Apply scaling: only borrow a fraction of available borrowing power
        amount_to_borrow = max_borrowable * ENTRY_SIZE_PCT
        logger.debug(f"[{timestamp.date()}] Scaling: Max borrowable ${max_borrowable:.2f} → Scaled to ${amount_to_borrow:.2f} ({ENTRY_SIZE_PCT:.0%})")
        
        # V13 COVERED BORROW: Limit debt to a multiple of our cash reserve
        # This prevents "naked leverage" where we cannot cover margin calls
        reserve_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
        max_covered_borrow = reserve_balance * MAX_DEBT_TO_RESERVE_RATIO
        
        if amount_to_borrow > max_covered_borrow:
            logger.info(
                f"[{timestamp.date()}] V13 COVERED BORROW: Limiting borrow to ${max_covered_borrow:.2f} "
                f"(Reserve: ${reserve_balance:.2f} × {MAX_DEBT_TO_RESERVE_RATIO}x). "
                f"Original amount: ${amount_to_borrow:.2f}"
            )
            amount_to_borrow = max_covered_borrow
        
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
            # REFACTOR: Call engine.borrow_funds() instead of manual state updates
            # This internalizes debt and balance management
            engine.borrow_funds(amount_to_borrow, engine.btc_price if hasattr(engine, 'btc_price') else 0)
            logger.info(f"[{timestamp.date()}] Empréstimo refinanciado: ${amount_to_borrow:.2f} (Projected HF: {projected_hf:.2f})")
        else:
            logger.info(f"[{timestamp.date()}] Empréstimo negado por guardrail de HF (Projected HF: {projected_hf:.2f} < {SAFE_HF_AFTER_BORROW})")
    
    def _execute_recursive_loop(
        self,
        row: pd.Series,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float,
        target_reserve: float
    ) -> None:
        """
        Execute recursive loop: use borrowed funds for 50% collateral, 50% LP.
        V3: Uses ATR for dynamic range calculation.
        """
        collateral_value = engine.btc_collateral_balance * current_price
        hf = (collateral_value * 0.80) / engine.total_debt_usd if engine.total_debt_usd > 0 else 999.0
        
        # Only deploy surplus cash beyond the dynamic reserve and gas buffer
        surplus_cash = max(0.0, engine.usd_balance - max(target_reserve, GAS_RESERVE_USD))
        
        if hf > HF_REFINANCE_THRESHOLD:
            available_for_loop = surplus_cash
            logger.debug(f"[{timestamp.date()}] HF={hf:.2f} > {HF_REFINANCE_THRESHOLD}: Usando alavancagem sobre surplus=${surplus_cash:.2f}")
        else:
            available_for_loop = surplus_cash - (surplus_cash * MIN_LIQUID_BUFFER)
            logger.debug(f"[{timestamp.date()}] HF={hf:.2f} <= {HF_REFINANCE_THRESHOLD}: Usando cash conservadoramente sobre surplus=${surplus_cash:.2f}")
        
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
        surplus_after = max(0.0, engine.usd_balance - max(target_reserve, GAS_RESERVE_USD))
        capital_for_lp_usd = max(0.0, surplus_after - (surplus_after * MIN_LIQUID_BUFFER))
        if capital_for_lp_usd > 1:
            # V7: Use directional range for profit-taking
            atr = row.get('ATR', 0.0)
            range_lower, range_upper = calculate_directional_range(current_price, atr, target_multiplier=15.0)
            logger.info(
                f"[{timestamp.date()}] Loop: Abrindo LP Directional (ATR={atr:.2f}) com ${capital_for_lp_usd:.2f} "
                f"(Range: ${range_lower:.2f}-${range_upper:.2f}) - Target Selling"
            )
            
            engine.open_lp(capital_for_lp_usd, range_lower, range_upper, current_price, timestamp, strategy="BULLISH_ML_DIRECTIONAL_V7")
        else:
            logger.debug(f"[{timestamp.date()}] Loop: Insuficiente para LP após buffer líquido.")
    
    def _execute_neutral_hodl(
        self,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float,
        target_reserve: float,
        row: pd.Series = None
    ) -> None:
        """
        V13 Heavy BTC Neutral State: 60% HODL + 40% LP.
        Instead of 100% LP, maintain higher BTC exposure during neutral periods.
        Target Split: ~60% Portfolio Value in HODL + ~40% in LP + ~20% USD Reserve.
        """
        # Calculate total equity snapshot with LP value for accurate reserve targeting
        total_equity, target_reserve, _ = self._calculate_equity_snapshot(engine, current_price)
        
        # Check if we already have sufficient reserve
        if engine.usd_balance >= target_reserve:
            # Reserve is adequate, now work on HODL vs LP split
            safe_balance = max(0.0, engine.usd_balance - target_reserve)
            
            # Calculate current HODL value and target HODL value
            current_hodl_value = engine.btc_hodl_balance * current_price
            target_hodl_value = total_equity * 0.60  # 60% of total equity
            
            # If HODL is below target, buy more BTC
            if current_hodl_value < target_hodl_value and safe_balance > 50.0:
                amount_to_buy = min(safe_balance, target_hodl_value - current_hodl_value)
                btc_to_buy = amount_to_buy / current_price if current_price > 0 else 0.0
                
                if btc_to_buy > 0.0001:
                    engine.buy_and_hodl(amount_to_buy, current_price)
                    logger.info(
                        f"[{timestamp.date()}] V13 NEUTRAL (Heavy BTC): Buying ${amount_to_buy:.2f} → {btc_to_buy:.6f} BTC HODL. "
                        f"Target: 60% HODL ({target_hodl_value:.2f}) | Current: {current_hodl_value:.2f}"
                    )
                    return
            
            # If HODL is at target, allocate remaining to LP (40% target)
            safe_balance_after = max(0.0, engine.usd_balance - target_reserve)
            if safe_balance_after > 50.0 and len(engine.active_lps) < MAX_ACTIVE_LPS:
                # Open wide symmetric LP for fee farming
                atr = row.get('ATR', 0.0) if row is not None else 0.0
                if atr > 0:
                    from backend.src.utils.math import calculate_dynamic_range
                    range_lower, range_upper = calculate_dynamic_range(
                        current_price, atr,
                        ATR_MULTIPLIER_NEUTRAL,
                        ATR_MULTIPLIER_NEUTRAL
                    )
                else:
                    range_lower = current_price * 0.70
                    range_upper = current_price * 1.60
                
                logger.info(
                    f"[{timestamp.date()}] V13 NEUTRAL (Heavy BTC): Opening Wide LP ${safe_balance_after:.2f} "
                    f"(Range: ${range_lower:.2f}-${range_upper:.2f}). Reserve: ${engine.usd_balance:.2f}"
                )
                engine.open_lp(safe_balance_after, range_lower, range_upper, current_price, timestamp, strategy="NEUTRAL_V13_HEAVY_BTC")
        else:
            # Reserve is below target - don't make any trades
            logger.debug(
                f"[{timestamp.date()}] V13 NEUTRAL: Reserve below target (${engine.usd_balance:.2f} < ${target_reserve:.2f}). "
                f"Holding position."
            )
    
    def _handle_post_leverage_state(
        self,
        row: pd.Series,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float,
        prediction: int,
        target_reserve: float
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
        estimated_gas_costs = engine.gas_fee_usd * 2
        max_allowable = max(0.0, engine.usd_balance - liquid_minimum - estimated_gas_costs - GAS_RESERVE_USD)
        capital_to_allocate = min(capital_to_allocate, max_allowable)
        
        if capital_to_allocate <= 10:
            logger.debug(
                f"[{timestamp.date()}] Saldo insuficiente para novo LP (Alocável: ${capital_to_allocate:.2f}, "
                f"Mínimo Líquido: ${liquid_minimum:.2f})"
            )
            return
        
        # Check Health Factor for margin reuse decision
        collateral_value = engine.btc_collateral_balance * current_price
        hf = (collateral_value * 0.80) / engine.total_debt_usd if engine.total_debt_usd > 0 else 999.0
        
        if prediction == 1:  # BULLISH
            self._execute_post_leverage_bullish(row, engine, timestamp, current_price, hf, capital_to_allocate, target_reserve)
        elif prediction == 0:  # NEUTRAL
            self._execute_post_leverage_neutral(row, engine, timestamp, current_price, hf, capital_to_allocate, target_reserve)
        else:
            logger.warning(f"[{timestamp.date()}] Unknown prediction value: {prediction}")
    
    def _execute_post_leverage_bullish(
        self,
        row: pd.Series,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float,
        hf: float,
        capital_to_allocate: float,
        target_reserve: float
    ) -> None:
        """
        Execute BULLISH post-leverage: ladder LP ranges and potentially refinance.
        V3: Uses ATR for dynamic range calculation with ladder adjustment.
        """
        # V7: Directional ranges with ladder adjustment for multiple LPs
        atr = row.get('ATR', 0.0)
        index = len(engine.active_lps)

        surplus_cash = max(0.0, engine.usd_balance - max(target_reserve, GAS_RESERVE_USD))
        capital_to_allocate = min(capital_to_allocate, surplus_cash)
        if capital_to_allocate <= 0:
            logger.debug(
                f"[{timestamp.date()}] BULLISH (V12 Sniper): Sem excedente após reserva dinâmica. Pulando novo LP."
            )
            return
        
        # Use directional range with ladder adjustment (reduce target multiplier for each additional LP)
        base_target = 15.0
        target_multiplier = max(8.0, base_target - (2.0 * index))  # Ladder down: 15, 13, 11, 9...
        range_lower, range_upper = calculate_directional_range(current_price, atr, target_multiplier)
        strategy_name = "BULLISH_ML_DIRECTIONAL_V12"
        
        # V12: REMOVED BLIND REFINANCING
        # Only open LPs with existing capital based on ENTRY_SIZE_PCT
        # No automatic borrowing just because HF is high - prevents over-leveraging at cycle tops
        
        logger.info(
            f"[{timestamp.date()}] BULLISH (V12 Sniper): Opening LP ${capital_to_allocate:.2f} | "
            f"HF={hf:.2f} | Líquido: ${engine.usd_balance - capital_to_allocate:.2f} "
            f"(Range: ${range_lower:.2f}-${range_upper:.2f})"
        )
        
        # Open LP
        if capital_to_allocate > 0 and len(engine.active_lps) < MAX_ACTIVE_LPS:
            engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp, strategy=strategy_name)
    
    def _execute_post_leverage_neutral(
        self,
        row: pd.Series,
        engine: 'TradingEngine',
        timestamp: pd.Timestamp,
        current_price: float,
        hf: float,
        capital_to_allocate: float,
        target_reserve: float
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
            if engine.usd_balance > engine.gas_fee_usd:
                # Pay down up to the excess_cash, but never more than outstanding debt
                payment_amount = min(excess_cash, engine.total_debt_usd)
                engine.total_debt_usd = max(0.0, engine.total_debt_usd - payment_amount)
                engine.usd_balance -= (payment_amount + engine.gas_fee_usd)
                logger.info(
                    f"[{timestamp.date()}] SMART REPAY: Using excess cash to pay down debt. "
                    f"Paid: ${payment_amount:.2f}, New Debt: ${engine.total_debt_usd:.2f}."
                )
                # Recompute capital_to_allocate after repayment
                safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
                capital_to_allocate = safe_balance * ENTRY_SIZE_PCT
                liquid_minimum = engine.usd_balance * MIN_LIQUID_BUFFER
                estimated_gas_costs = engine.gas_fee_usd * 2
                max_allowable = max(0.0, engine.usd_balance - liquid_minimum - estimated_gas_costs - GAS_RESERVE_USD)
                capital_to_allocate = min(capital_to_allocate, max_allowable)

            surplus_cash = max(0.0, engine.usd_balance - max(target_reserve, GAS_RESERVE_USD))
            capital_to_allocate = min(capital_to_allocate, surplus_cash)
        
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
