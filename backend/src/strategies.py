import pandas as pd
import logging
from backtester import Backtester, LOAN_TO_VALUE_RATIO 
from regime_analyzer import analyze_market_regime
# --- MUDANÇA 1: Importar o DB_FILE ---
from config import DB_FILE

logger = logging.getLogger(__name__)

DAYS_OUT_OF_RANGE_THRESHOLD = 10 

def run_strategy_regime_switcher(row: pd.Series, engine: Backtester, timestamp: pd.Timestamp):
    """
    Estratégia V4 (Market Timing Loop)
    - Espera o primeiro sinal 'BEARISH' para comprar colateral e iniciar o loop.
    - Depois, gerencia as LPs de 'farm' e 'compra'.
    """
    
    current_price = row['Close']

    # --- 1. LÓGICA DE FECHAMENTO (Sempre checar se tivermos LPs) ---
    if engine.active_lps:
        for lp in engine.active_lps.copy():
            if lp['days_out_of_range'] > DAYS_OUT_OF_RANGE_THRESHOLD:
                logger.info(
                    f"[{timestamp.date()}] FECHANDO LP {lp['id']}: Fora do range "
                    f"por {lp['days_out_of_range']} dias. Preço atual: ${current_price:.2f}"
                )
                engine.close_lp(lp_id=lp['id'], current_btc_price=current_price, timestamp=timestamp)

    # --- 2. LÓGICA DE ABERTURA ---
    regime = analyze_market_regime(row)
    
    
    # == ESTADO 1: Pré-Empréstimo (Esperando o sinal de compra) ==
    if engine.total_debt_usd == 0:
        
        if regime == 'BEARISH':
            # --- É O SINAL! HORA DE COMPRAR O COLATERAL E INICIAR O LOOP ---
            logger.info(
                f"[{timestamp.date()}] PRIMEIRO SINAL BEARISH (Compra). "
                f"Comprando colateral inicial com ${engine.usd_balance:.2f} @ ${current_price:.2f}"
            )
            # 1. Comprar colateral (Ponto 1)
            engine.buy_and_hodl(engine.usd_balance, current_price) # Gasta todo o usd_balance (agora é 0)
            
            # 2. Pegar Empréstimo (Ponto 2)
            collateral_value = engine.btc_hodl_balance * current_price
            amount_to_borrow = collateral_value * LOAN_TO_VALUE_RATIO
            engine.total_debt_usd += amount_to_borrow
            engine.usd_balance += amount_to_borrow # usd_balance agora é (ex) 500
            logger.info(f"[{timestamp.date()}] Loop: Pegando empréstimo de ${amount_to_borrow:.2f} (50% LTV)")
            
            # 3. Executar Loop Recursivo (Ponto 3)
            btc_bought = engine.usd_balance / current_price # 500 / 100 = 5 BTC
                        
            btc_to_collateral = btc_bought * 0.50 # 2.5 BTC
            btc_to_lp = btc_bought * 0.50         # 2.5 BTC
            
            # --- CORREÇÃO DO BUG DE LÓGICA (Gastar o dinheiro) ---
            # 4. Adicionar ao colateral (gasta 50% do caixa)
            capital_for_collateral_usd = btc_to_collateral * current_price # 2.5 * 100 = $250
            engine.add_collateral(btc_to_collateral)
            engine.usd_balance -= capital_for_collateral_usd # 500 - 250 = 250
            logger.info(f"[{timestamp.date()}] Loop: {btc_to_collateral:.6f} BTC adicionado ao colateral.")
            
            # 5. Abrir LP (gasta os 50% restantes do caixa)
            # --- CORREÇÃO DO BUG (UnboundLocalError) ---
            capital_for_lp_usd = engine.usd_balance # Usa o que sobrou ($250)
            range_lower = current_price * 0.70 # Range Largo de Compra
            range_upper = current_price * 1.60
            
            logger.info(f"[{timestamp.date()}] Loop: Abrindo LP de Range Largo com ${capital_for_lp_usd:.2f} (Range: ${range_lower:.2f}-${range_upper:.2f})")
            engine.open_lp(capital_for_lp_usd, range_lower, range_upper, current_price, timestamp, strategy="BEARISH_LOOP")
            engine.usd_balance -= capital_for_lp_usd # 250 - 250 = 0
            
        else:
            # Regime é SIDEWAYS ou BULL_TOP...
            logger.debug(f"[{timestamp.date()}] Em caixa (USD), esperando sinal BEARISH para comprar.")
            pass # Continuar 100% em USD
    
    # == ESTADO 2: Pós-Empréstimo (Já estamos alavancados e operando) ==
    else:
        if not engine.active_lps:
            capital_to_allocate = engine.usd_balance
            if capital_to_allocate <= 10:
                return # Caixa de juros está baixo, não abrir LP

            if regime == 'BEARISH':
                range_lower = current_price * 0.70 
                range_upper = current_price * 1.60
                logger.info(f"[{timestamp.date()}] Regime: BEARISH (Pós-Loop). Abrindo LP de Range Largo (Range: ${range_lower:.2f}-${range_upper:.2f})")
                engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp, strategy="BEARISH_LOOP")
                engine.usd_balance -= capital_to_allocate # Deduz o capital
            
            elif regime == 'SIDEWAYS':
                range_lower = current_price * 0.85 
                range_upper = current_price * 1.15
                logger.info(f"[{timestamp.date()}] Regime: SIDEWAYS (Pós-Loop). Abrindo LP de Farm (Range: ${range_lower:.2f}-${range_upper:.2f})")
                engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp, strategy="SIDEWAYS_FARM")
                engine.usd_balance -= capital_to_allocate # Deduz o capital

            elif regime == 'BULL_TOP':
                logger.info(f"[{timestamp.date()}] Regime: BULL_TOP (Pós-Loop). Guardando caixa para pagar juros.")
                pass

