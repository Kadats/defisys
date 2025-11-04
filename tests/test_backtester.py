import pytest
import pandas as pd
import math
from backend.src.backtester import Backtester # Ajuste o caminho se necessário

@pytest.fixture
def fresh_backtester():
    """Retorna uma instância nova do Backtester com $1000."""
    return Backtester(initial_capital_usd=1000.0)

def test_open_lp_price_below_range(fresh_backtester):
    """
    Testa a abertura de LP quando o preço está ABAIXO do range.
    A posição deve ser 100% em BTC (Ativo X).
    """
    bt = fresh_backtester
    capital_to_open = 100.0
    range_lower = 150.0
    range_upper = 200.0
    current_price = 100.0 # < range_lower
    
    bt.open_lp(capital_to_open, range_lower, range_upper, current_price, pd.Timestamp('2025-01-01'))
    
    # 1. Verifica se o capital foi debitado
    assert bt.usd_balance == 900.0
    # 2. Verifica se a LP foi criada
    assert len(bt.active_lps) == 1
    
    lp = bt.active_lps[0]
    
    # 3. Verifica a composição (100% BTC)
    expected_btc = capital_to_open / current_price # 100.0 / 100.0 = 1.0 BTC
    assert lp['initial_amount_usdt'] == 0.0
    assert lp['initial_amount_btc'] == pytest.approx(expected_btc)
    assert lp['L'] > 0 # Liquidez foi calculada

def test_open_lp_price_above_range(fresh_backtester):
    """
    Testa a abertura de LP quando o preço está ACIMA do range.
    A posição deve ser 100% em USDT (Ativo Y).
    """
    bt = fresh_backtester
    capital_to_open = 250.0
    range_lower = 150.0
    range_upper = 200.0
    current_price = 300.0 # > range_upper
    
    bt.open_lp(capital_to_open, range_lower, range_upper, current_price, pd.Timestamp('2025-01-01'))
    
    # 1. Verifica se o capital foi debitado
    assert bt.usd_balance == 750.0
    # 2. Verifica se a LP foi criada
    assert len(bt.active_lps) == 1
    
    lp = bt.active_lps[0]
    
    # 3. Verifica a composição (100% USDT)
    assert lp['initial_amount_usdt'] == pytest.approx(capital_to_open)
    assert lp['initial_amount_btc'] == 0.0
    assert lp['L'] > 0 # Liquidez foi calculada

def test_open_lp_price_within_range(fresh_backtester):
    """
    Testa a abertura de LP quando o preço está DENTRO do range.
    A posição deve ser um mix de BTC e USDT.
    Usamos "números mágicos" (quadrados perfeitos) para facilitar a validação.
    """
    bt = fresh_backtester
    capital_to_open = 1000.0 # Vamos alocar todo o capital
    range_lower = 100.0 # sqrt(100) = 10
    range_upper = 400.0 # sqrt(400) = 20
    current_price = 225.0 # sqrt(225) = 15
    
    bt.open_lp(capital_to_open, range_lower, range_upper, current_price, pd.Timestamp('2025-01-01'))
    
    # 1. Verifica se o capital foi debitado
    assert bt.usd_balance == 0.0
    # 2. Verifica se a LP foi criada
    assert len(bt.active_lps) == 1
    
    lp = bt.active_lps[0]

    # 3. Verifica a composição (Mix de BTC e USDT)
    # Com base nos cálculos que fizemos no passo anterior:
    # L = 1000 / (2*15 - 10 - 225/20) = 1000 / (30 - 10 - 11.25) = 1000 / 8.75 = 114.2857...
    # amount_usdt = L * (15 - 10) = 114.2857 * 5 = 571.428...
    # amount_btc = L * ( (1/15) - (1/20) ) = 114.2857 * 0.01666... = 1.90476...
    
    expected_L = 114.285714
    expected_usdt = 571.428571
    expected_btc = 1.904761
    
    assert lp['initial_amount_usdt'] == pytest.approx(expected_usdt)
    assert lp['initial_amount_btc'] == pytest.approx(expected_btc)
    assert lp['L'] == pytest.approx(expected_L)
    
    # 4. Verifica o custo total (a verificação mais importante)
    total_cost = lp['initial_amount_usdt'] + (lp['initial_amount_btc'] * current_price)
    assert total_cost == pytest.approx(capital_to_open, rel=1e-3)