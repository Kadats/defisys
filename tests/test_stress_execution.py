import pytest
import pandas as pd
from backend.src.core.trading_engine import TradingEngine

def test_high_slippage_execution():
    """
    Teste 1 (High Slippage): Instancie o TradingEngine com slippage_pct=0.05 (5%). 
    Simule uma compra de BTC e verifique se o valor de BTC recebido na carteira 
    é 5% menor do que o preço teórico current_price indicaria.
    """
    initial_capital = 1000.0
    current_price = 50000.0
    slippage_pct = 0.05
    gas_fee = 0.0 # Zerar gas para isolar slippage no teste
    
    # Instanciar engine com alto slippage
    engine = TradingEngine(initial_capital_usd=initial_capital, slippage_pct=slippage_pct, gas_fee_usd=gas_fee)
    
    amount_to_buy = 500.0
    engine.buy_and_hodl(amount_to_buy, current_price, timestamp=pd.Timestamp.now())
    
    # Preço efetivo esperado: 50000 * (1 + 0.05) = 52500
    # BTC esperado: 500 / 52500 = 0.0095238...
    expected_btc = amount_to_buy / (current_price * (1 + slippage_pct))
    
    assert pytest.approx(engine.btc_hodl_balance, rel=1e-5) == expected_btc
    assert engine.usd_balance == initial_capital - amount_to_buy

def test_high_gas_fees_execution():
    """
    Teste 2 (High Gas Fees): Instancie o TradingEngine com gas_fee_usd=150.0. 
    Verifique se o saldo em USD é drenado em exatos $150 ao executar uma operação.
    Teste também se a função _check_and_harvest ignora a coleta se a taxa acumulada 
    não compensar esse Gas absurdo.
    """
    initial_capital = 1000.0
    current_price = 50000.0
    gas_fee = 150.0
    
    engine = TradingEngine(initial_capital_usd=initial_capital, gas_fee_usd=gas_fee)
    
    # Operação 1: Compra
    engine.buy_and_hodl(100.0, current_price, timestamp=pd.Timestamp.now())
    # Saldo esperado: 1000 - 100 - 150 = 750
    assert engine.usd_balance == 750.0
    
    # Operação 2: Harvest com taxas baixas
    # Criar uma LP fake com taxas acumuladas menores que 25 * gas_fee
    # 25 * 150 = 3750
    lp = {
        'id': 1,
        'L': 1.0,
        'range_lower': 40000.0,
        'range_upper': 60000.0,
        'fees_accrued_usdt': 500.0, # < 3750
        'fees_accrued_btc': 0.0
    }
    engine.active_lps = [lp]
    
    # Tentar harvest
    engine._check_and_harvest(current_price, timestamp=pd.Timestamp.now())
    
    # O saldo não deve ter mudado (harvest ignorado)
    assert engine.usd_balance == 750.0
    assert lp['fees_accrued_usdt'] == 500.0
    
    # Harvest com taxas altas
    lp['fees_accrued_usdt'] = 4000.0 # > 3750
    engine._check_and_harvest(current_price, timestamp=pd.Timestamp.now())
    
    # O saldo deve ter aumentado: 750 + 4000 - 150 (gas) = 4600
    assert engine.usd_balance == 4600.0
    assert lp['fees_accrued_usdt'] == 0.0
