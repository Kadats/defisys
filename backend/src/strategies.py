import pandas as pd
import logging
from .backtester import Backtester, LOAN_TO_VALUE_RATIO 
from .regime_analyzer import analyze_market_regime
from .config import (
    DB_FILE, GAS_RESERVE_USD, MIN_LIQUID_BUFFER, MAX_ALLOCATION_PCT, 
    BASE_ALLOCATION_PCT, DRAWDOWN_THRESHOLD, FNG_THRESHOLD_AGGRESSIVE
)
from .config import SIMULATED_GAS_FEE_USD, TRAIN_TEST_SPLIT_DATE, HF_REFINANCE_THRESHOLD, SAFE_HF_AFTER_BORROW, MAX_ACTIVE_LPS, ENTRY_SIZE_PCT

logger = logging.getLogger(__name__)

DAYS_OUT_OF_RANGE_THRESHOLD = 10


def calculate_safe_borrow_amount(
    collateral_value: float,
    current_debt: float,
    target_hf: float,
    min_borrow: float = 10.0
) -> float:
    """
    Calculate the maximum safe borrow amount to keep HF above target after borrowing.
    
    Args:
        collateral_value: Current collateral value (BTC holdings * price)
        current_debt: Current debt in USD
        target_hf: Minimum acceptable HF immediately after borrow (e.g., 1.6)
        min_borrow: Minimum borrow amount to return (default $10)
    
    Returns:
        Safe borrow amount in USD, or 0.0 if borrow would breach safety threshold
    
    Logic:
        - Target equation: (collateral_value * 0.8) / (current_debt + safe_borrow) = target_hf
        - Solve for safe_borrow: safe_borrow = (collateral_value * 0.8) / target_hf - current_debt
        - If safe_borrow < 0 or < min_borrow threshold, return 0.0 (no safe borrow possible)
    """
    if target_hf <= 0 or collateral_value <= 0:
        return 0.0
    
    # Calculate maximum debt that keeps HF at target level
    max_safe_debt = (collateral_value * 0.8) / target_hf
    
    # Calculate safe borrow as the difference from current debt
    safe_borrow = max_safe_debt - current_debt
    
    # Only borrow if it's a meaningful amount
    if safe_borrow >= min_borrow:
        return safe_borrow
    else:
        return 0.0


def calculate_entry_size(usd_balance: float, current_price: float, ath_price: float, fng_value: float) -> float:
    """
    V4 Dynamic Allocation: Calculate position size based on market conditions.
    
    Args:
        usd_balance: Current USD balance in the portfolio
        current_price: Current BTC price
        ath_price: All-Time High price to calculate drawdown
        fng_value: Fear & Greed Index value (0-100)
    
    Returns:
        allocation_pct: Percentage of balance to allocate (0.0 to 0.8)
    
    Logic:
        - Start with BASE_ALLOCATION_PCT (20%)
        - If drawdown > 30%, increase allocation aggressively (70-80%)
        - If FNG < 20 (Extreme Fear), increase allocation aggressively (70-80%)
        - Never allocate more than MAX_ALLOCATION_PCT (80%)
        - Always keep at least MIN_LIQUID_BUFFER (20%) as cash reserve
    """
    if ath_price <= 0:
        return BASE_ALLOCATION_PCT
    
    # Calculate drawdown from ATH
    drawdown = (ath_price - current_price) / ath_price
    
    # Start with base allocation
    allocation_pct = BASE_ALLOCATION_PCT
    
    # Aggressive buying: Deep drawdown (price far below ATH)
    if drawdown > DRAWDOWN_THRESHOLD:
        allocation_pct = 0.70
        logger.info(f"[DYNAMIC] Drawdown {drawdown:.1%} > Threshold. Aggressive allocation: {allocation_pct:.0%}")
    
    # Extreme fear index: Buy more when sentiment is very negative
    if fng_value < FNG_THRESHOLD_AGGRESSIVE:
        allocation_pct = max(allocation_pct, 0.70)
        logger.info(f"[DYNAMIC] FNG {fng_value:.0f} < Threshold {FNG_THRESHOLD_AGGRESSIVE}. Aggressive allocation: {allocation_pct:.0%}")
    
    # Cap at maximum allocation
    allocation_pct = min(allocation_pct, MAX_ALLOCATION_PCT)
    
    # Ensure we never breach the minimum liquid buffer
    # If allocation would leave us < MIN_LIQUID_BUFFER, reduce it
    max_allocable = 1.0 - MIN_LIQUID_BUFFER
    allocation_pct = min(allocation_pct, max_allocable)
    
    return allocation_pct 

def run_strategy_regime_switcher(row: pd.Series, engine: Backtester, timestamp: pd.Timestamp):
    """
    Estratégia V7 (BTC Standard Lite)
    - Usa a coluna 'prediction' (do modelo de ML) para tomar decisões.
    - Default: Hold BTC (not USD) to track Bitcoin price appreciation
    - 'prediction == 1' (Modelo prevê SUBIDA) -> Sinal BULLISH (Leverage Existing Collateral + Amplify)
    - 'prediction == 0' (Modelo prevê estabilidade) -> BTC HODL (Convert excess USD to BTC, no leverage)
    """
    
    current_price = row['Close']

    # --- 1. LÓGICA DE FECHAMENTO (Permanece a mesma) ---
    if engine.active_lps:
        for lp in engine.active_lps.copy():
            if lp['days_out_of_range'] > DAYS_OUT_OF_RANGE_THRESHOLD:
                # ... (lógica de fechar LP) ...
                engine.close_lp(lp_id=lp['id'], current_btc_price=current_price, timestamp=timestamp)

    # --- 2. LÓGICA DE ABERTURA ---
    
    # --- MUDANÇA 2: Ler a predição do modelo (do DataFrame) se existir ---
    # O 'prediction_engine' pode ter adicionado esta coluna ao 'row'.
    # 1 = Previu Subida (BULLISH), 0 = Previu Estabilidade/Queda (NEUTRO)
    prediction = row.get('prediction', None)
    if prediction is None:
        # Backward-compatibility: if no prediction is present, use the legacy regime analyzer
        regime = analyze_market_regime(row)
        prediction = 1 if regime == 'BULLISH' else 0
    
    
    # == ESTADO 1: Pré-Empréstimo (Esperando o sinal BULLISH) ==
    if engine.total_debt_usd == 0:
        
        # O sinal de compra agora é a previsão de SUBIDA do modelo
        if prediction == 1: # (Previu SUBIDA - oportunidade de compra/amplificar)
            # --- BTC STANDARD: Leverage existing collateral or buy new BTC before amplifying ---
            
            # V4: Calculate position size based on market conditions
            ath_price = row.get('ATH_52w', current_price * 1.5)  # Fallback to 1.5x if ATH not available
            fng_value = row.get('FNG_Value', 50)  # Fallback to neutral if FNG not available
            
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
            #    If so, we can skip buying and go straight to borrowing against existing collateral
            if engine.btc_hodl_balance > 0.0001:
                logger.info(
                    f"[{timestamp.date()}] BULLISH: Leverage existing BTC collateral ({engine.btc_hodl_balance:.6f} BTC). "
                    f"Skipping buy, proceeding to amplify via borrowing."
                )
            else:
                # No existing BTC: Buy new collateral with allocation
                engine.buy_and_hodl(capital_to_allocate, current_price)
                logger.info(f"[{timestamp.date()}] BULLISH: No existing BTC. Buying {capital_to_allocate/current_price:.6f} BTC as collateral.")
            
            # 2. Pegar Empréstimo (Margin Reuse: Borrow based on collateral - old or new)
            # PRE-BORROW HF SIMULATION: Ensure HF stays above SAFE_HF_AFTER_BORROW
            collateral_value = engine.btc_hodl_balance * current_price
            amount_to_borrow = collateral_value * LOAN_TO_VALUE_RATIO
            logger.debug(f"[{timestamp.date()}] BULLISH: Collateral = {engine.btc_hodl_balance:.6f} BTC @ ${current_price:.2f} = ${collateral_value:.2f}")
            
            # Simulate HF after borrow
            projected_debt = engine.total_debt_usd + amount_to_borrow
            projected_hf = (collateral_value * 0.8) / projected_debt if projected_debt > 0 else 999.0
            
            # If projected HF falls below safety threshold, adjust the borrow amount
            if projected_hf < SAFE_HF_AFTER_BORROW:
                # Recalculate safe borrow to maintain target HF
                amount_to_borrow = calculate_safe_borrow_amount(
                    collateral_value, 
                    engine.total_debt_usd, 
                    SAFE_HF_AFTER_BORROW,
                    min_borrow=10.0
                )
                if amount_to_borrow > 0:
                    logger.debug(
                        f"[{timestamp.date()}] HF Guardrail: Reduced borrow from full LTV to ${amount_to_borrow:.2f} "
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
            
            # 3. Executar Loop Recursivo (Respeitando Margin Reuse Logic)
            # NOTE: Use an absolute GAS_RESERVE_USD exclusion so we never consume the gas reserve.
            collateral_value = engine.btc_hodl_balance * current_price
            hf = (collateral_value * 0.80) / engine.total_debt_usd if engine.total_debt_usd > 0 else 999.0

            # Base safe balance excludes the absolute gas reserve
            safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)

            if hf > HF_REFINANCE_THRESHOLD:
                # SAFE: Use the entire safe balance (reserve preserved)
                available_for_loop = safe_balance
                logger.debug(f"[{timestamp.date()}] HF={hf:.2f} > {HF_REFINANCE_THRESHOLD}: Usando alavancagem (refinanciamento) sobre safe_balance=${safe_balance:.2f}")
            else:
                # CAREFUL: Use a conservative portion of the safe balance, preserving MIN_LIQUID_BUFFER of the safe_balance
                available_for_loop = safe_balance - (safe_balance * MIN_LIQUID_BUFFER)
                logger.debug(f"[{timestamp.date()}] HF={hf:.2f} <= {HF_REFINANCE_THRESHOLD}: Usando cash conservadoramente sobre safe_balance=${safe_balance:.2f}")

            # Guard against negative available
            available_for_loop = max(0.0, available_for_loop)

            btc_bought = available_for_loop / current_price if current_price > 0 else 0.0
            btc_to_collateral = btc_bought * 0.50
            btc_to_lp = btc_bought * 0.50

            # 4. Adicionar ao colateral (deduzir do saldo real)
            capital_for_collateral_usd = btc_to_collateral * current_price
            if capital_for_collateral_usd > 1:
                engine.add_collateral(btc_to_collateral)
                engine.usd_balance -= capital_for_collateral_usd
                logger.info(f"[{timestamp.date()}] Loop: {btc_to_collateral:.6f} BTC adicionado ao colateral.")

            # 5. Abrir LP (Respeitando liquid buffer computed from remaining safe balance)
            safe_balance_after = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
            capital_for_lp_usd = max(0.0, safe_balance_after - (safe_balance_after * MIN_LIQUID_BUFFER))
            if capital_for_lp_usd > 1:
                range_lower = current_price * 0.70
                range_upper = current_price * 1.60

                logger.info(f"[{timestamp.date()}] Loop: Abrindo LP Range Amplo com ${capital_for_lp_usd:.2f} (Range: ${range_lower:.2f}-${range_upper:.2f})")
                engine.open_lp(capital_for_lp_usd, range_lower, range_upper, current_price, timestamp, strategy="BULLISH_ML_DYNAMIC")
                engine.usd_balance -= capital_for_lp_usd
            else:
                logger.debug(f"[{timestamp.date()}] Loop: Insuficiente para LP após buffer líquido.")
            
        else: # (prediction == 0)
            # BTC STANDARD LITE: Convert excess USD to BTC HODL during neutral periods
            # This ensures we participate in Bitcoin's price appreciation even without leverage
            safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
            liquid_minimum = safe_balance * MIN_LIQUID_BUFFER
            excess_usd = max(0.0, safe_balance - liquid_minimum)
            
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
    
    # == ESTADO 2: Pós-Empréstimo (Já estamos alavancados e operando) ==
    else:
        # Allow opening additional LPs up to MAX_ACTIVE_LPS (multi-pool scaling)
        if len(engine.active_lps) < MAX_ACTIVE_LPS:
            # V4 Dynamic Allocation for ESTADO 2 (per-entry sizing uses ENTRY_SIZE_PCT of safe balance)
            ath_price = row.get('ATH_52w', current_price * 1.5)
            fng_value = row.get('FNG_Value', 50)

            # Respect absolute gas reserve before allocating
            safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)

            # Each new entry should use a fixed fraction of the safe balance
            capital_to_allocate = safe_balance * ENTRY_SIZE_PCT

            # Also ensure we keep minimum liquid buffer (interest + safety) and gas for txs
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
            
            if prediction == 1: # BULLISH
                # Ladder ranges so each new LP has slightly offset bounds relative to existing LPs
                index = len(engine.active_lps)
                step = 0.06
                range_lower = current_price * max(0.01, (0.70 + step * index))
                range_upper = current_price * max(range_lower / current_price + 0.05, (1.60 - step * index))
                strategy_name = "BULLISH_ML_DYNAMIC"

                if hf > HF_REFINANCE_THRESHOLD:
                    # PRE-BORROW HF SIMULATION: Calculate safe borrow amount
                    collateral_value = engine.btc_hodl_balance * current_price
                    safe_borrow = calculate_safe_borrow_amount(
                        collateral_value,
                        engine.total_debt_usd,
                        SAFE_HF_AFTER_BORROW,
                        min_borrow=10.0
                    )
                    
                    if safe_borrow > 0:
                        # Cap the borrow at what we wanted to allocate
                        amount_to_borrow = min(safe_borrow, capital_to_allocate)
                        engine.total_debt_usd += amount_to_borrow
                        engine.usd_balance += amount_to_borrow
                        logger.info(f"[{timestamp.date()}] HF={hf:.2f} > {HF_REFINANCE_THRESHOLD}: Refinanciamento (${amount_to_borrow:.2f}, Safe HF={SAFE_HF_AFTER_BORROW})")
                        capital_to_allocate = amount_to_borrow
                    else:
                        logger.debug(
                            f"[{timestamp.date()}] HF Guardrail: Cannot borrow despite HF={hf:.2f} (would breach {SAFE_HF_AFTER_BORROW})"
                        )
                
                logger.info(f"[{timestamp.date()}] BULLISH (V6): LP Range Amplo ${capital_to_allocate:.2f} | HF={hf:.2f} | Líquido: ${engine.usd_balance - capital_to_allocate:.2f} (Range: ${range_lower:.2f}-${range_upper:.2f})")

            
            elif prediction == 0: # NEUTRAL
                # BTC STANDARD: In neutral markets with existing debt, hold collateral and farm fees
                # Don't aggressively borrow; instead conservatively farm LP fees to pay down debt
                if capital_to_allocate <= 0:
                    logger.info(
                        f"[{timestamp.date()}] NEUTRAL (V7 BTC Standard): Leverage already deployed. "
                        f"HF={hf:.2f} (Target: {HF_REFINANCE_THRESHOLD}). "
                        f"Holding collateral & farming fees to service debt."
                    )
                    return
                
                # Conservative farming: Only use minimal capital for LP fees
                range_lower = current_price * 0.70
                range_upper = current_price * 1.60
                strategy_name = "NEUTRAL_ML_DYNAMIC_V7"
                
                # Don't refinance aggressively in neutral mode - keep debt stable
                logger.info(
                    f"[{timestamp.date()}] NEUTRAL (V7 BTC Standard): Conservative LP Farm ${capital_to_allocate:.2f} | "
                    f"HF={hf:.2f} | Líquido: ${engine.usd_balance - capital_to_allocate:.2f} (Range: ${range_lower:.2f}-${range_upper:.2f})"
                )

            
            else:
                logger.warning(f"[{timestamp.date()}] Unknown prediction value: {prediction}")
                return
            
            # Open LP with dynamically calculated capital (respect MAX_ACTIVE_LPS)
            if capital_to_allocate > 0 and len(engine.active_lps) < MAX_ACTIVE_LPS:
                engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp, strategy=strategy_name)
                engine.usd_balance -= capital_to_allocate