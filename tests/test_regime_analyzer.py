import pytest
import pandas as pd
from backend.src.regime_analyzer import (
    analyze_market_regime,
    FNG_FEAR_THRESHOLD,
    FNG_GREED,
    RSI_BEAR_THRESHOLD,
    RSI_BULL
)

def create_mock_row(price: float, sma_50: float, rsi: float, fng: float) -> pd.Series:
    """Cria uma linha de DataFrame (Pandas Series) para simular os dados."""
    data = {
        'Close': price,
        'SMA_50': sma_50,
        'RSI': rsi,
        'FNG_Value': fng # Certifique-se que o nome da coluna aqui bate com o data_provider
    }
    return pd.Series(data)


# --- Testes de BEARISH (Compra) ---
def test_regime_is_bearish_on_fear():
    """Testa se o regime é BEARISH baseado no F&G Baixo (Medo)."""
    # Preço abaixo da média E Medo Extremo (RSI é neutro)
    row = create_mock_row(price=90, sma_50=100, rsi=50, fng=FNG_FEAR_THRESHOLD)
    regime = analyze_market_regime(row)
    assert regime == 'BEARISH'

def test_regime_is_bearish_on_rsi():
    """Testa se o regime é BEARISH baseado no RSI Baixo."""
    # Preço abaixo da média E RSI Baixo (F&G é neutro)
    row = create_mock_row(price=90, sma_50=100, rsi=RSI_BEAR_THRESHOLD, fng=50)
    regime = analyze_market_regime(row)
    assert regime == 'BEARISH'

def test_regime_is_bull_top_on_fng_greed():
    """Testa se o regime é BULL_TOP baseado na Ganância Extrema (F&G)."""
    # Preço acima da média E F&G em euforia
    row = create_mock_row(price=110, sma_50=100, rsi=60, fng=FNG_GREED)
    regime = analyze_market_regime(row)
    assert regime == 'BULL_TOP'

def test_regime_is_bull_top_on_rsi_bull():
    """Testa se o regime é BULL_TOP baseado no RSI Sobrecomprado."""
    # Preço acima da média E RSI em euforia
    row = create_mock_row(price=110, sma_50=100, rsi=RSI_BULL, fng=50)
    regime = analyze_market_regime(row)
    assert regime == 'BULL_TOP'

# --- Testes de SIDEWAYS (Farm) ---
def test_regime_is_sideways_on_healthy_bull_trend():
    """
    Testa se o regime é SIDEWAYS (Farm) durante uma tendência de alta saudável
    (que NÃO é euforia).
    """
    # Preço acima da média, mas F&G e RSI estão neutros/saudáveis
    row = create_mock_row(
        price=110, 
        sma_50=100, 
        rsi=(RSI_BULL - 1), # Abaixo da euforia
        fng=(FNG_GREED - 1)  # Abaixo da euforia
    ) 
    regime = analyze_market_regime(row)
    assert regime == 'SIDEWAYS'

def test_regime_is_sideways_on_price_cross():
    """Testa se o regime é SIDEWAYS se o preço estiver "em cima" da média."""
    # Preço muito próximo da média (RSI e F&G neutros)
    row = create_mock_row(price=100, sma_50=100, rsi=50, fng=50)
    regime = analyze_market_regime(row)
    assert regime == 'SIDEWAYS'

def test_regime_is_sideways_on_conflicting_signals():
    """Testa se o regime é SIDEWAYS se os sinais forem conflitantes."""
    # Preço acima da média (sugere alta), mas F&G com medo (sugere baixa)
    # Nossa lógica atual prioriza a tendência (preço > sma) e só entra em BULLISH se o RSI for alto
    # Como o RSI é neutro, deve cair em SIDEWAYS.
    row = create_mock_row(price=110, sma_50=100, rsi=50, fng=FNG_FEAR_THRESHOLD)
    regime = analyze_market_regime(row)
    assert regime == 'SIDEWAYS'

