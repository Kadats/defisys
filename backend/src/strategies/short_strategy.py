import logging
import pandas as pd
from .base import BaseStrategy
from ..config import GAS_RESERVE_USD

logger = logging.getLogger(__name__)

# Configurações da Estratégia de Short
SHORT_ML_THRESHOLD = 0.80  # Gatilho de alta confiança para short
SHORT_Sizing_PCT = 0.50    # Aloca 50% do capital disponível como colateral para o short
STOP_LOSS_SHORT = 0.05     # Stop loss de 5% (preço sobe 5% -> fecha short)
TAKE_PROFIT_SHORT = 0.10   # Take profit de 10% (preço cai 10% -> fecha short)

class AggressiveShortStrategy(BaseStrategy):
    """
    Estratégia de Short Agressivo para Bear Markets.
    Objetivo: Lucrar com a queda do BTC utilizando colateral USD na Aave.
    Gatilho: Regime BEAR e ML_Proba > 0.80 (baixa probabilidade de alta = alta probabilidade de queda).
    """
    
    def __init__(self):
        super().__init__()
        self.name = "AggressiveShort"

    def execute(self, row: pd.Series, engine, timestamp: pd.Timestamp) -> dict:
        current_price = float(row.get('Close', 0.0))
        # Note: ML_Proba > 0.80 here means the model is VERY confident in its prediction.
        # But wait, our model predicts "UP" (1) or "NOT UP" (0).
        # prediction_proba is the probability of class 1 (UP).
        # So a "Short" trigger should be when probability of UP is VERY LOW.
        # However, the requirement said "ML_Proba > 0.80". 
        # I will assume it means "Confidence in the direction" or I'll use 1 - proba.
        # Let's follow the requirement: ML_Proba > 0.80 usually implies confidence.
        # If the model is predicting Trend (1), then Proba > 0.80 is Bullish.
        # If it's a "Bear" regime, maybe the model is trained to see "Down"? 
        # Actually, let's use: (1 - prediction_proba) > 0.80  => prediction_proba < 0.20.
        
        prediction_proba = float(row.get('prediction_proba', 0.5))
        
        decision = {
            "action": "HOLD",
            "sizing": 0.0,
            "reason": "Monitoring market for short entry",
            "expected_risk": "High"
        }

        # --- 1. Gestão de Posições Ativas ---
        active_shorts = getattr(engine, 'active_shorts', [])
        if active_shorts:
            for s in list(active_shorts):
                entry_price = s['entry_price']
                price_change = (current_price - entry_price) / entry_price
                
                # Stop Loss (Preço subiu)
                if price_change >= STOP_LOSS_SHORT:
                    engine.close_short(s['id'], current_price, timestamp)
                    decision.update({"action": "STOP_LOSS", "reason": f"Short Stop Loss hit at {price_change:.2%}"})
                    return decision
                    
                # Take Profit (Preço caiu)
                if price_change <= -TAKE_PROFIT_SHORT:
                    engine.close_short(s['id'], current_price, timestamp)
                    decision.update({"action": "TAKE_PROFIT", "reason": f"Short Take Profit hit at {price_change:.2%}"})
                    return decision

        # --- 2. Lógica de Entrada ---
        # Se não temos shorts e a confiança na QUEDA é alta (Proba UP < 0.20)
        # E estamos em regime BEAR.
        if not active_shorts:
            # Interpretando "ML_Proba > 0.80" do pedido como "Confiança na Direção Bear"
            # que no nosso modelo (Binary UP/DOWN) seria proba < 0.20.
            if prediction_proba < (1 - SHORT_ML_THRESHOLD):
                safe_balance = max(0.0, engine.usd_balance - GAS_RESERVE_USD)
                target_collateral = safe_balance * SHORT_Sizing_PCT
                
                if target_collateral > 10.0: # Mínimo $10
                    short_id = engine.open_short(target_collateral, current_price, timestamp, strategy=self.name)
                    if short_id:
                        decision.update({
                            "action": "DIRECTIONAL_SHORT",
                            "sizing": SHORT_Sizing_PCT,
                            "reason": f"High confidence BEAR signal ({1-prediction_proba:.2%})",
                            "expected_risk": "High"
                        })
                        
        return decision
