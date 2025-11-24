import pandas as pd
import logging
from .backtester import Backtester, LOAN_TO_VALUE_RATIO 
from .regime_analyzer import analyze_market_regime
from .config import DB_FILE, GAS_RESERVE_USD

logger = logging.getLogger(__name__)

DAYS_OUT_OF_RANGE_THRESHOLD = 10 

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
            # --- É O SINAL! HORA DE COMPRAR O COLATERAL E INICIAR O LOOP ---
            # Apply gas buffer: keep GAS_RESERVE_USD in cash for operational costs
            available_capital = engine.usd_balance - GAS_RESERVE_USD
            if available_capital <= 0:
                logger.warning(
                    f"[{timestamp.date()}] Sinal BEARISH recebido, mas capital insuficiente "
                    f"(USD: ${engine.usd_balance:.2f}, Reserva: ${GAS_RESERVE_USD:.2f}). Aguardando mais caixa."
                )
                return
            
            logger.info(
                f"[{timestamp.date()}] PRIMEIRO SINAL 'BEARISH' (ML Previu Queda). "
                f"Comprando colateral inicial com ${available_capital:.2f} @ ${current_price:.2f} "
                f"(Reserva: ${GAS_RESERVE_USD:.2f})"
            )
            # ... (Toda a lógica do Loop Recursivo permanece exatamente a mesma) ...
            # 1. Comprar colateral
            engine.buy_and_hodl(available_capital, current_price) 
            
            # 2. Pegar Empréstimo
            collateral_value = engine.btc_hodl_balance * current_price
            amount_to_borrow = collateral_value * LOAN_TO_VALUE_RATIO
            engine.total_debt_usd += amount_to_borrow
            engine.usd_balance += amount_to_borrow 
            logger.info(f"[{timestamp.date()}] Loop: Pegando empréstimo de ${amount_to_borrow:.2f} (50% LTV)")
            
            # 3. Executar Loop Recursivo (Respeitando GAS_RESERVE)
            available_for_loop = engine.usd_balance - GAS_RESERVE_USD
            btc_bought = available_for_loop / current_price 
            btc_to_collateral = btc_bought * 0.50 
            btc_to_lp = btc_bought * 0.50         
            
            # 4. Adicionar ao colateral
            capital_for_collateral_usd = btc_to_collateral * current_price 
            engine.add_collateral(btc_to_collateral)
            engine.usd_balance -= capital_for_collateral_usd 
            logger.info(f"[{timestamp.date()}] Loop: {btc_to_collateral:.6f} BTC adicionado ao colateral.")
            
            # 5. Abrir LP (Respeitando GAS_RESERVE)
            capital_for_lp_usd = engine.usd_balance - GAS_RESERVE_USD
            if capital_for_lp_usd > 1:
                range_lower = current_price * 0.70 
                range_upper = current_price * 1.60
                
                logger.info(f"[{timestamp.date()}] Loop: Abrindo LP de Range Largo com ${capital_for_lp_usd:.2f} (Range: ${range_lower:.2f}-${range_upper:.2f})")
                engine.open_lp(capital_for_lp_usd, range_lower, range_upper, current_price, timestamp, strategy="BEARISH_ML_LOOP")
                engine.usd_balance -= capital_for_lp_usd 
            else:
                logger.debug(f"[{timestamp.date()}] Loop: Capital insuficiente para abrir LP após GAS_RESERVE.") 
            
        else: # (prediction == 0)
            # Modelo prevê estabilidade (SIDEWAYS), mas ainda não entramos...
            logger.debug(f"[{timestamp.date()}] Em caixa (USD), modelo prevê estabilidade. Esperando sinal 'BEARISH_ML'.")
            pass # Continuar 100% em USD
    
    # == ESTADO 2: Pós-Empréstimo (Já estamos alavancados e operando) ==
    else:
        if not engine.active_lps:
            # Apply gas buffer: always keep GAS_RESERVE_USD for operational costs
            capital_to_allocate = engine.usd_balance - GAS_RESERVE_USD
            if capital_to_allocate <= 10:
                logger.debug(
                    f"[{timestamp.date()}] Saldo insuficiente para LP (USD: ${engine.usd_balance:.2f}, "
                    f"após reserva: ${capital_to_allocate:.2f}, mínimo: $10.00)"
                )
                return 

            if prediction == 1: # (Equivalente ao antigo 'regime == BEARISH')
                range_lower = current_price * 0.70 
                range_upper = current_price * 1.60
                logger.info(f"[{timestamp.date()}] Regime: BEARISH (ML). Abrindo LP de Range Largo com ${capital_to_allocate:.2f} (Reserva: ${GAS_RESERVE_USD:.2f}) (Range: ${range_lower:.2f}-${range_upper:.2f})")
                engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp, strategy="BEARISH_ML_LOOP")
                engine.usd_balance -= capital_to_allocate 
            
            elif prediction == 0: # (Equivalente ao antigo 'regime == SIDEWAYS')
                range_lower = current_price * 0.85 
                range_upper = current_price * 1.15
                logger.info(f"[{timestamp.date()}] Regime: SIDEWAYS (ML). Abrindo LP de Farm com ${capital_to_allocate:.2f} (Reserva: ${GAS_RESERVE_USD:.2f}) (Range: ${range_lower:.2f}-${range_upper:.2f})")
                engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp, strategy="SIDEWAYS_ML_FARM")
                engine.usd_balance -= capital_to_allocate 

            # Não temos mais 'BULL_TOP', o modelo cuida disso (prevendo 0)