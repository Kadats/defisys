# Em backend/src/strategies.py
import pandas as pd
import logging
# Importamos a classe Backtester para type hinting (boa prática)
from .backtester import Backtester 

logger = logging.getLogger(__name__)

# --- Lógica de Decisão Antiga (Preservada) ---
def _decide_action_v1(row: pd.Series) -> str:
    """
    Decide a ação ('range_curto', 'range_largo', 'reduzir') com base nos scores.
    Esta é a lógica do blueprint original. Renomeada para clareza.
    """
    # Limiares (thresholds) - mantemos os mesmos por enquanto
    OPP_HIGH_THRESHOLD = 0.5
    VOL_SAFE_THRESHOLD = 0.3
    
    opportunity_score = row.get('Oportunidade_Score', 0.5) # Usa 0.5 se score não existir
    volatility_score = row.get('Volatilidade_Score', 0.5)

    if opportunity_score > OPP_HIGH_THRESHOLD and volatility_score < VOL_SAFE_THRESHOLD:
        return 'range_curto'
    elif opportunity_score > OPP_HIGH_THRESHOLD and volatility_score >= VOL_SAFE_THRESHOLD:
        return 'range_largo'
    else:
        return 'reduzir'

# --- Nova Função de Execução da Estratégia ---
def run_strategy_v1(row: pd.Series, engine: Backtester, timestamp: pd.Timestamp):
    """
    Função principal da estratégia V1 (Blueprint).
    Recebe a linha de dados atual ('row'), o motor de backtest ('engine') e o timestamp.
    Analisa os dados e chama os métodos do motor para executar ações.
    """
    decision = _decide_action_v1(row)
    current_price = row['Close']
    # 'timestamp' agora é recebido como argumento

    # Lógica de Gestão de Posição (Simplificada para UMA posição)
    
    active_lp = engine.active_lps[0] if engine.active_lps else None

    # 1. Se a decisão for REDUZIR e houver LP ativa, fechar.
    if decision == 'reduzir' and active_lp:
        # --- MUDANÇA: Passar o timestamp para o log ---
        engine.close_lp(lp_id=active_lp['id'], current_btc_price=current_price, timestamp=timestamp)

    # 2. Se a decisão for ENTRAR (curto ou largo) e NÃO houver LP ativa, abrir.
    elif decision in ['range_curto', 'range_largo'] and not active_lp:
        atr_multiplier = 0.75 if decision == 'range_curto' else 2.0
        range_width = row['ATR'] * atr_multiplier
        range_lower = current_price - range_width
        range_upper = current_price + range_width
        
        capital_to_allocate = engine.usd_balance
        if capital_to_allocate > 10:
            engine.open_lp(
                capital_usd=capital_to_allocate,
                range_lower=range_lower,
                range_upper=range_upper,
                current_btc_price=current_price,
                timestamp=timestamp
            )

    # 3. Se a decisão MUDAR (curto -> largo ou vice-versa) e houver LP ativa, ajustar.
    elif decision in ['range_curto', 'range_largo'] and active_lp and decision != active_lp.get('type', decision):
        logger.info(f"[{timestamp.date()}] AJUSTE DE RANGE: Mudando de {active_lp.get('type')} para {decision}...")
        
        # --- MUDANÇA: Passar o timestamp para o log ---
        engine.close_lp(lp_id=active_lp['id'], current_btc_price=current_price, timestamp=timestamp)
        
        # (A reabertura ocorrerá no próximo passo, quando 'active_lp' for None)

