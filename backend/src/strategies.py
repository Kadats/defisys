import pandas as pd
import logging
from .backtester import Backtester 
from .regime_analyzer import analyze_market_regime

logger = logging.getLogger(__name__)

def run_strategy_regime_switcher(row: pd.Series, engine: Backtester, timestamp: pd.Timestamp):
    """
    Estratégia 'Regime Contrário V1' (Buy Fear, Sell Greed).
    """
    
    regime = analyze_market_regime(row)
    current_price = row['Close']
    active_lp = engine.active_lps[0] if engine.active_lps else None

    
    # 1. REGIME DE BAIXA ('BEARISH') -> SINAL DE COMPRA
    # Meta: Comprar a baixa com um range largo.
    if regime == 'BEARISH':
        if not active_lp:
            # Abrir uma LP de "Compra/Hold"
            range_lower = current_price * 0.75 # Range -25%
            range_upper = current_price * 1.50 # Range +50%
            
            capital_to_allocate = engine.usd_balance
            if capital_to_allocate > 10:
                logger.info(f"[{timestamp.date()}] Regime: BEARISH (Compra). Abrindo LP de Range Largo (Range: ${range_lower:.2f}-${range_upper:.2f})")
                engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp)
        else:
            # Já estamos comprados/posicionados, não fazer nada.
            pass
    
    # 2. REGIME LATERAL ('SIDEWAYS') -> SINAL DE FARM
    # Meta: Farm de taxas com range apertado.
    elif regime == 'SIDEWAYS':
        if not active_lp:
            # Abrir uma nova LP de farm
            range_width = current_price * 0.10 # Range apertado de +/- 10%
            range_lower = current_price - range_width
            range_upper = current_price + range_width
            
            capital_to_allocate = engine.usd_balance
            if capital_to_allocate > 10:
                logger.info(f"[{timestamp.date()}] Regime: SIDEWAYS (Farm). Abrindo LP de Farm (Range: ${range_lower:.2f}-${range_upper:.2f})")
                engine.open_lp(capital_to_allocate, range_lower, range_upper, current_price, timestamp)
        else:
            # (Opcional Futuro): Se a LP anterior era 'BEARISH' (larga), talvez fechar e abrir uma 'SIDEWAYS' (apertada).
            # Por enquanto, V1: se já tem LP, deixa estar.
            pass
            
    # 3. REGIME DE ALTA ('BULLISH') -> SINAL DE VENDA
    # Meta: Realizar lucros, sair do mercado, esperar próxima baixa.
    elif regime == 'BULLISH':
        if active_lp:
            logger.info(f"[{timestamp.date()}] Regime: BULLISH (Venda). Fechando LP {active_lp['id']} para realizar lucros.")
            engine.close_lp(lp_id=active_lp['id'], current_btc_price=current_price, timestamp=timestamp)