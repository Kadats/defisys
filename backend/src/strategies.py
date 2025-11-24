import pandas as pd
import logging
from .backtester import Backtester, LOAN_TO_VALUE_RATIO 
from .regime_analyzer import analyze_market_regime
from .config import (
    DB_FILE, GAS_RESERVE_USD, MIN_LIQUID_BUFFER, MAX_ALLOCATION_PCT, 
    BASE_ALLOCATION_PCT, DRAWDOWN_THRESHOLD, FNG_THRESHOLD_AGGRESSIVE
)

logger = logging.getLogger(__name__)

DAYS_OUT_OF_RANGE_THRESHOLD = 10


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
    Estratégia V5 (AI Prediction Model)
    - Usa a coluna 'prediction' (do modelo de ML) para tomar decisões.
    - 'prediction == 1' (Modelo prevê queda) -> Sinal de COMPRA (BEARISH)
    - 'prediction == 0' (Modelo prevê estabilidade) -> Sinal de FARM (SIDEWAYS)
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
    # 1 = Previu Queda (BEARISH), 0 = Previu Estabilidade (SIDEWAYS)
    prediction = row.get('prediction', None)
    if prediction is None:
        # Backward-compatibility: if no prediction is present, use the legacy regime analyzer
        regime = analyze_market_regime(row)
        prediction = 1 if regime == 'BEARISH' else 0
    
    
    # == ESTADO 1: Pré-Empréstimo (Esperando o sinal de compra) ==
    if engine.total_debt_usd == 0:
        
        # O sinal de compra agora é a previsão do modelo
        if prediction == 1: # (Equivalente ao antigo 'regime == BEARISH')
            # --- É O SINAL! HORA DE COMPRAR O COLATERAL E INICIAR O LOOP (V4 Dynamic) ---
            
            # V4: Calculate position size based on market conditions
            ath_price = row.get('ATH_52w', current_price * 1.5)  # Fallback to 1.5x if ATH not available
            fng_value = row.get('FNG_Value', 50)  # Fallback to neutral if FNG not available
            
            allocation_pct = calculate_entry_size(engine.usd_balance, current_price, ath_price, fng_value)
            capital_to_allocate = engine.usd_balance * allocation_pct
            
            # Ensure we keep minimum liquid buffer
            liquid_minimum = engine.usd_balance * MIN_LIQUID_BUFFER
            capital_to_allocate = min(capital_to_allocate, engine.usd_balance - liquid_minimum)
            
            if capital_to_allocate < 10:
                logger.debug(
                    f"[{timestamp.date()}] Sinal BEARISH, mas capital insuficiente para alavancagem "
                    f"(Alocável: ${capital_to_allocate:.2f}, Mínimo Líquido: ${liquid_minimum:.2f})"
                )
                return
            
            logger.info(
                f"[{timestamp.date()}] PRIMEIRA POSIÇÃO 'BEARISH' (V4 Dynamic). "
                f"Alocação: {allocation_pct:.0%} | Capital: ${capital_to_allocate:.2f} @ ${current_price:.2f} "
                f"| Mantendo líquido: ${engine.usd_balance - capital_to_allocate:.2f}"
            )
            
            # 1. Comprar colateral com alocação dinâmica
            engine.buy_and_hodl(capital_to_allocate, current_price) 
            
            # 2. Pegar Empréstimo (Margin Reuse: Borrow based on new collateral)
            collateral_value = engine.btc_hodl_balance * current_price
            amount_to_borrow = collateral_value * LOAN_TO_VALUE_RATIO
            engine.total_debt_usd += amount_to_borrow
            engine.usd_balance += amount_to_borrow 
            logger.info(f"[{timestamp.date()}] Empréstimo refinanciado: ${amount_to_borrow:.2f} (50% LTV)")
            
            # 3. Executar Loop Recursivo (Respeitando Margin Reuse Logic)
            # Se HF > 2.5, preferir emprestar mais. Senão, usar cash.
            collateral_value = engine.btc_hodl_balance * current_price
            hf = (collateral_value * 0.80) / engine.total_debt_usd if engine.total_debt_usd > 0 else 999.0
            
            if hf > 2.5:
                # SAFE: Borrow more instead of using cash
                available_for_loop = engine.usd_balance
                logger.debug(f"[{timestamp.date()}] HF={hf:.2f} > 2.5: Usando alavancagem (refinanciamento)")
            else:
                # CAREFUL: Use available cash, preserve liquid buffer
                available_for_loop = engine.usd_balance - (engine.usd_balance * MIN_LIQUID_BUFFER)
                logger.debug(f"[{timestamp.date()}] HF={hf:.2f} <= 2.5: Usando cash conservadoramente")
            
            btc_bought = available_for_loop / current_price 
            btc_to_collateral = btc_bought * 0.50 
            btc_to_lp = btc_bought * 0.50         
            
            # 4. Adicionar ao colateral
            capital_for_collateral_usd = btc_to_collateral * current_price 
            if capital_for_collateral_usd > 1:
                engine.add_collateral(btc_to_collateral)
                engine.usd_balance -= capital_for_collateral_usd 
                logger.info(f"[{timestamp.date()}] Loop: {btc_to_collateral:.6f} BTC adicionado ao colateral.")
            
            # 5. Abrir LP (Respeitando liquid buffer)
            capital_for_lp_usd = max(0, engine.usd_balance - (engine.usd_balance * MIN_LIQUID_BUFFER))
            if capital_for_lp_usd > 1:
                range_lower = current_price * 0.70 
                range_upper = current_price * 1.60
                
                logger.info(f"[{timestamp.date()}] Loop: Abrindo LP Range Largo com ${capital_for_lp_usd:.2f} (Range: ${range_lower:.2f}-${range_upper:.2f})")
                engine.open_lp(capital_for_lp_usd, range_lower, range_upper, current_price, timestamp, strategy="BEARISH_ML_DYNAMIC")
                engine.usd_balance -= capital_for_lp_usd 
            else:
                logger.debug(f"[{timestamp.date()}] Loop: Insuficiente para LP após buffer líquido.") 
            
        else: # (prediction == 0)
            # Modelo prevê estabilidade (SIDEWAYS), mas ainda não entramos...
            logger.debug(f"[{timestamp.date()}] Em caixa (USD), modelo prevê estabilidade. Esperando sinal 'BEARISH_ML'.")
            pass # Continuar 100% em USD
    
    # == ESTADO 2: Pós-Empréstimo (Já estamos alavancados e operando) ==
    else:
        if not engine.active_lps:
            # V4 Dynamic Allocation for ESTADO 2
            ath_price = row.get('ATH_52w', current_price * 1.5)
            fng_value = row.get('FNG_Value', 50)
            
            allocation_pct = calculate_entry_size(engine.usd_balance, current_price, ath_price, fng_value)
            capital_to_allocate = engine.usd_balance * allocation_pct
            
            # Ensure we keep minimum liquid buffer for interest + gas
            liquid_minimum = engine.usd_balance * MIN_LIQUID_BUFFER
            capital_to_allocate = min(capital_to_allocate, engine.usd_balance - liquid_minimum)
            
            if capital_to_allocate <= 10:
                logger.debug(
                    f"[{timestamp.date()}] Saldo insuficiente para LP (Alocável: ${capital_to_allocate:.2f}, "
                    f"Mínimo Líquido: ${liquid_minimum:.2f})"
                )
                return 
            
            # Check Health Factor for margin reuse decision
            collateral_value = engine.btc_hodl_balance * current_price
            hf = (collateral_value * 0.80) / engine.total_debt_usd if engine.total_debt_usd > 0 else 999.0
            
            if prediction == 1: # BEARISH
                range_lower = current_price * 0.70 
                range_upper = current_price * 1.60
                strategy_name = "BEARISH_ML_DYNAMIC"
                
                if hf > 2.5:
                    # SAFE: Use margin (borrow more) instead of cash
                    # Borrow to fund the LP without touching cash
                    amount_to_borrow = capital_to_allocate
                    engine.total_debt_usd += amount_to_borrow
                    engine.usd_balance += amount_to_borrow
                    logger.info(f"[{timestamp.date()}] HF={hf:.2f} > 2.5: Refinanciamento (${amount_to_borrow:.2f})")
                    capital_to_allocate = amount_to_borrow
                
                logger.info(f"[{timestamp.date()}] BEARISH (V4): LP Range Largo ${capital_to_allocate:.2f} | HF={hf:.2f} | Líquido: ${engine.usd_balance - capital_to_allocate:.2f} (Range: ${range_lower:.2f}-${range_upper:.2f})")
            
            elif prediction == 0: # SIDEWAYS
                range_lower = current_price * 0.85 
                range_upper = current_price * 1.15
                strategy_name = "SIDEWAYS_ML_DYNAMIC"
                
                if hf > 2.5:
                    # SAFE: Use margin
                    amount_to_borrow = capital_to_allocate
                    engine.total_debt_usd += amount_to_borrow
                    engine.usd_balance += amount_to_borrow
                    logger.info(f"[{timestamp.date()}] HF={hf:.2f} > 2.5: Refinanciamento (${amount_to_borrow:.2f})")
                    capital_to_allocate = amount_to_borrow
                
                logger.info(f"[{timestamp.date()}] SIDEWAYS (V4): LP Farm ${capital_to_allocate:.2f} | HF={hf:.2f} | Líquido: ${engine.usd_balance - capital_to_allocate:.2f} (Range: ${range_lower:.2f}-${range_upper:.2f})")
            
            else:
                return
            
            # Open LP with dynamically calculated capital
            engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp, strategy=strategy_name)
            engine.usd_balance -= capital_to_allocate