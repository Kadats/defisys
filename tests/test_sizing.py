import pytest
import pandas as pd
from backend.src.core.trading_engine import TradingEngine
from backend.src.core.risk_manager import RiskManager

def test_risk_manager_adjust_position_size():
    rm = RiskManager(gas_reserve_usd=50.0, simulated_gas_fee_usd=1.0)
    
    # 1. Normal case: requested size easily fits within balance
    adjusted = rm.adjust_position_size(
        requested_capital=100.0,
        current_balance=200.0,
        gas_fee_usd=1.0,
        min_reserve_usd=50.0
    )
    assert adjusted == 100.0
    
    # 2. Insufficient balance: requested > available. Max safe is 200 - 1 - 50 = 149
    adjusted = rm.adjust_position_size(
        requested_capital=300.0,
        current_balance=200.0,
        gas_fee_usd=1.0,
        min_reserve_usd=50.0
    )
    assert adjusted == 149.0
    
    # 3. Bankrupt: Balance too low to even cover reserves
    adjusted = rm.adjust_position_size(
        requested_capital=100.0,
        current_balance=40.0,
        gas_fee_usd=1.0,
        min_reserve_usd=50.0
    )
    assert adjusted == 0.0

def test_trading_engine_open_lp_auto_adjusts_size(caplog):
    """
    Testa se o TradingEngine auto-ajusta o tamanho de uma LP caso o pedido
    exceda o saldo útil em vez de lançar exceção.
    """
    import logging
    caplog.set_level(logging.INFO)
    
    engine = TradingEngine(initial_capital_usd=151.0, gas_fee_usd=1.0)
    ts = pd.Timestamp.now()
    
    # Tentamos abrir uma LP de $300 (muito maior que o saldo)
    # A reserva é 0 nesse mock simplificado ou usa o default (GAS_RESERVE_USD).
    # Com gas_fee_usd = 1.0, se deixarmos a min_reserve_usd=0 no teste de motor (ou o default que é 50):
    # Max disponivel = 151 - 1 (gas) = 150 (se sem reserva, senao 100)
    # Vamos assumir que o risk_manager dele tem gas_reserve_usd = 50.0
    # O ajuste sera para: 151 - 1 - 50 = 100.
    
    # Como não temos mock do BD aqui, vamos forçar uma exceção na inserção de BD 
    # apenas para testar a logica de negócio. 
    # Melhor: mockar log_open_position
    import backend.src.core.trading_engine as te
    original_log_open = te.log_open_position
    te.log_open_position = lambda *args, **kwargs: 999
    
    try:
        engine.open_lp(
            capital_usd=300.0,
            range_lower=40000,
            range_upper=60000,
            current_btc_price=50000.0,
            timestamp=ts,
            strategy="TEST"
        )
        
        # Confirma que foi ajustado!
        assert len(engine.active_lps) == 1
        opened_lp = engine.active_lps[0]
        # O initial_capital_usd deve ter sido ajustado para 100.0 (151 - 1(gas) - 50(gas_reserve))
        assert opened_lp["initial_capital_usd"] == 100.0
        
        # O saldo restante deve ser a reserva exata (pois consumiu tudo até a reserva)
        # Saldo: 151.0 - 1.0 (gas) - 100.0 (capital ajustado) = 50.0
        assert engine.usd_balance == 50.0
        
        # Verificar o log formatado
        assert "[BALANCE_INFO]" in caplog.text
        assert "Requested: $300.00 | Available: $100.00 | Adjusted: $100.00" in caplog.text
        
    finally:
        te.log_open_position = original_log_open
