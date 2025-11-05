import pandas as pd

# Limiares de Decisão (V2 - Refinados)
FNG_FEAR_THRESHOLD = 30
FNG_GREED = 80 # Euforia/Ganância Extrema
RSI_BEAR_THRESHOLD = 40
RSI_BULL = 75 # Sobrecobrado/Euforia

def analyze_market_regime(row: pd.Series) -> str:
    """
    Analisa os indicadores para decidir que TIPO de LP abrir, 
    caso estejamos sem posição.
    Retorna: 'BEARISH' (Comprar), 'SIDEWAYS' (Farm), 'BULL_TOP' (Não Fazer Nada).
    """
    
    price = row.get('Close', 0)
    sma_trend = row.get('SMA_50', price) 
    rsi = row.get('RSI', 50) 
    fng_value = row.get('FNG_Value', 50)

    # 1. Condição de Topo (BULL_TOP) -> Sinal de "Não Comprar"
    # Preço acima da tendência E (ganância extrema OU RSI sobrecomprado)
    is_bull_top = (price > sma_trend) and (fng_value >= FNG_GREED or rsi >= RSI_BULL)
    if is_bull_top:
        return 'BULL_TOP'
        
    # 2. Condição de Fundo (BEARISH) -> Sinal de "Comprar"
    # Preço abaixo da tendência E (medo OU momentum de baixa)
    is_bearish = (price < sma_trend) and (fng_value <= FNG_FEAR_THRESHOLD or rsi <= RSI_BEAR_THRESHOLD)
    if is_bearish:
        return 'BEARISH'

    # 3. Condição Padrão (SIDEWAYS) -> Sinal de "Farm"
    # (Inclui a "Tendência de Alta Saudável")
    return 'SIDEWAYS'

