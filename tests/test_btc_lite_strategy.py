import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from backend.src.core.trading_engine import TradingEngine
from backend.src.strategies.btc_lite import BTCLiteStrategy

@pytest.fixture
def mocked_db():
    with patch('backend.src.core.trading_engine.log_open_position', return_value=1) as mock_open, \
         patch('backend.src.core.trading_engine.log_close_position', return_value=None) as mock_close:
        yield mock_open, mock_close

def test_btc_lite_hf_uses_collateral_not_hodl(mocked_db):
    """
    Testa se o BTCLiteStrategy usa o saldo de colateral, e não o de HODL, 
    para calcular o Health Factor e decidir sobre alavancagem / deleveraging.
    """
    # Cria o engine com $1000
    engine = TradingEngine(initial_capital_usd=1000.0)
    strategy = BTCLiteStrategy()

    # Configura cenário onde há BTC no HODL mas NENHUM no colateral
    current_price = 100000.0
    engine.btc_hodl_balance = 0.5  # 0.5 BTC = $50000
    engine.btc_collateral_balance = 0.0 # Sem colateral
    engine.total_debt_usd = 10000.0 # Dívida de $10000
    
    # Com 0 no colateral e $10000 de dívida, o HF deve ser 0.0
    # O smart deleveraging na estratégia não deve usar engine.btc_hodl_balance
    # Se usasse hodl_balance, hf seria (50000 * 0.8) / 10000 = 4.0 (não acionaria)
    
    row = pd.Series({'Close': current_price, 'prediction': 1})
    timestamp = pd.Timestamp('2026-04-05')
    
    # Executamos o método diretamente para inspecionar seu comportamento
    # Se a lógica usar hodl, ela achará que o HF é 4.0 e retornará sem deleveraging
    # Se usar collateral, o HF é 0.0 e tentará usar caixa
    
    initial_debt = engine.total_debt_usd
    
    # Chamamos o método privado de deleveraging
    strategy._handle_smart_deleveraging(engine, current_price, timestamp)
    
    # Como não temos colateral, HF = 0 < 1.6 (DELEVERAGE_THRESHOLD_HF)
    # A estratégia tentará usar o USD balance para pagar a dívida.
    # O saldo disponível é (1000 - gas_reserve). Gas reserve é 50 no RiskManager default, 
    # mas precisamos checar _handle_smart_deleveraging que faz:
    # available_cash = max(0, engine.usd_balance - GAS_RESERVE_USD) -> 1000 - 50 = 950
    # payment_amount = min(950, 10000) = 950
    # Esperamos que a dívida reduza se usou o collateral (HF = 0).
    
    assert engine.total_debt_usd < initial_debt, "A estratégia não tentou pagar a dívida. Provavelmente está usando btc_hodl_balance para calcular o HF (falso seguro)."

