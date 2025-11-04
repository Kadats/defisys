import pandas as pd
import logging
from .backtester import Backtester 
# --- MUDANÇA 1: Importar o novo módulo ---
from .regime_analyzer import analyze_market_regime

logger = logging.getLogger(__name__)

# --- MUDANÇA 2: Renomear a função para refletir a nova lógica ---
def run_strategy_regime_switcher(row: pd.Series, engine: Backtester, timestamp: pd.Timestamp):
    """
    Estratégia principal que usa o 'Regime Analyzer' para tomar decisões.
    """
    
    # --- MUDANÇA 3: A análise agora é uma única chamada de função ---
    regime = analyze_market_regime(row)
    
    current_price = row['Close']
    active_lp = engine.active_lps[0] if engine.active_lps else None

    # --- MUDANÇA 4: Lógica de 'switch' baseada no regime ---
    
    # 1. REGIME DE BAIXA ('BEARISH')
    # Meta: Sair do mercado, preservar capital.
    if regime == 'BEARISH':
        if active_lp:
            logger.info(f"[{timestamp.date()}] Regime: BEARISH. Fechando LP {active_lp['id']} para preservar capital.")
            engine.close_lp(lp_id=active_lp['id'], current_btc_price=current_price, timestamp=timestamp)
    
    # 2. REGIME LATERAL ('SIDEWAYS')
    # Meta: Farm de taxas com range apertado.
    elif regime == 'SIDEWAYS':
        if not active_lp:
            # Abrir uma nova LP de farm
            range_width = current_price * 0.10 # Range apertado de +/- 10%
            range_lower = current_price - range_width
            range_upper = current_price + range_width
            
            capital_to_allocate = engine.usd_balance
            if capital_to_allocate > 10:
                logger.info(f"[{timestamp.date()}] Regime: SIDEWAYS. Abrindo LP de Farm (Range: ${range_lower:.2f}-${range_upper:.2f})")
                engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp)
        else:
            # (Opcional Futuro): Verificar se a LP atual ainda é um bom range de farm
            pass 
            
    # 3. REGIME DE ALTA ('BULLISH')
    # Meta: Comprar/Vender com range largo.
    elif regime == 'BULLISH':
        if not active_lp:
            # Abrir uma nova LP de range largo
            range_width = current_price * 0.25 # Range largo de +/- 25%
            range_lower = current_price - range_width
            range_upper = current_price + range_width
            
            capital_to_allocate = engine.usd_balance
            if capital_to_allocate > 10:
                logger.info(f"[{timestamp.date()}] Regime: BULLISH. Abrindo LP de Range Largo (Range: ${range_lower:.2f}-${range_upper:.2f})")
                engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp)
        else:
            # (Opcional Futuro): Ajustar o range da LP de alta
            pass

