import pandas as pd

# Limiares de Decisão (V1 - Podemos ajustar após o backtest)
FNG_FEAR_THRESHOLD = 30    # Fear & Greed abaixo de 30 = Medo
RSI_BULL_THRESHOLD = 60    # RSI acima de 60 = Momentum de alta
RSI_BEAR_THRESHOLD = 40    # RSI abaixo de 40 = Momentum de baixa

def analyze_market_regime(row: pd.Series) -> str:
    """
    Analisa os indicadores da linha (row) para classificar o regime de mercado.
    Retorna: 'BULLISH', 'BEARISH', ou 'SIDEWAYS'.
    """
    
    # Coleta os indicadores (com valores padrão caso não existam)
    price = row.get('Close', 0)
    sma_20 = row.get('SMA_20', price) # Usa o próprio preço se SMA não existir
    rsi = row.get('RSI', 50) # Começa neutro
    fng_value = row.get('FNG_Value', 50) # Começa neutro (do F&G)

    # --- Lógica de Decisão V1 ---
    
    # 1. Condição de Baixa (BEARISH)
    # Tendência de baixa (preço < média) E (medo extremo OU momentum de baixa)
    is_bearish = (price < sma_20) and (fng_value <= FNG_FEAR_THRESHOLD or rsi <= RSI_BEAR_THRESHOLD)
    if is_bearish:
        return 'BEARISH'
        
    # 2. Condição de Alta (BULLISH)
    # Tendência de alta (preço > média) E (momentum de alta)
    is_bullish = (price > sma_20) and (rsi >= RSI_BULL_THRESHOLD)
    if is_bullish:
        return 'BULLISH'

    # 3. Condição Padrão (SIDEWAYS)
    # Se não for nenhum dos anteriores, o mercado está lateralizado/indefinido.
    return 'SIDEWAYS'

    