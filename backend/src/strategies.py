import pandas as pd
import logging
from .backtester import Backtester 
from .regime_analyzer import analyze_market_regime

logger = logging.getLogger(__name__)

DAYS_OUT_OF_RANGE_THRESHOLD = 10

def run_strategy_regime_switcher(row: pd.Series, engine: Backtester, timestamp: pd.Timestamp):
    """
    Estratégia V2 (Avançada)
    - Lógica de Fechamento: Fecha LPs "mortas" (fora do range por X dias).
    - Lógica de Abertura: Chama o 'regime_analyzer' APENAS se não houver LPs.
    """
    
    current_price = row['Close']

    # --- 1. LÓGICA DE FECHAMENTO (Sempre checar) ---
    lp_was_closed_this_turn = False
    for lp in engine.active_lps.copy():
        
        if lp['days_out_of_range'] > DAYS_OUT_OF_RANGE_THRESHOLD:
            logger.info(
                f"[{timestamp.date()}] FECHANDO LP {lp['id']}: Fora do range "
                f"(${lp['range_lower']:.2f}-${lp['range_upper']:.2f}) "
                f"por {lp['days_out_of_range']} dias. Preço atual: ${current_price:.2f}"
            )
            engine.close_lp(lp_id=lp['id'], current_btc_price=current_price, timestamp=timestamp)
            lp_was_closed_this_turn = True # Marca que fechamos uma LP

    # --- MUDANÇA AQUI: Se fechamos uma LP, não fazemos mais nada hoje ---
    if lp_was_closed_this_turn:
        return # Espera até a próxima vela para decidir o que fazer

    # --- 2. LÓGICA DE ABERTURA (Apenas se não tivermos LPs) ---
    if not engine.active_lps:
        # Estamos com 100% de capital livre. O que fazemos?
        regime = analyze_market_regime(row)
        capital_to_allocate = engine.usd_balance

        if capital_to_allocate <= 10:
            return # Capital insuficiente

        # 2.1. Regime BEARISH (Medo) -> Comprar a baixa
        if regime == 'BEARISH':
            range_lower = current_price * 0.70 # Range -30%
            range_upper = current_price * 1.60 # Range +60%
            logger.info(f"[{timestamp.date()}] Regime: BEARISH (Compra). Abrindo LP de Range Largo (Range: ${range_lower:.2f}-${range_upper:.2f})")
            engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp)
        
        # 2.2. Regime SIDEWAYS (Neutro/Farm) -> Farmar taxas
        elif regime == 'SIDEWAYS':
            range_lower = current_price * 0.85 # Range +/- 15%
            range_upper = current_price * 1.15
            logger.info(f"[{timestamp.date()}] Regime: SIDEWAYS (Farm). Abrindo LP de Range Apertado (Range: ${range_lower:.2f}-${range_upper:.2f})")
            engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp)

        # 2.3. Regime BULL_TOP (Euforia) -> Não fazer nada
        elif regime == 'BULL_TOP':
            logger.info(f"[{timestamp.date()}] Regime: BULL_TOP (Euforia). Não fazer nada, esperando a próxima baixa.")
            pass # Ficar em USD, não comprar o topo

