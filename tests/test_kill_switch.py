import pytest
import pandas as pd
from backend.src.core.trading_engine import TradingEngine
from backend.src.core.risk_manager import RiskManager

def test_kill_switch_emergency_shutdown():
    """Testa a execução direta do emergency_shutdown no TradingEngine."""
    engine = TradingEngine(initial_capital_usd=1000.0, gas_fee_usd=1.0)
    ts = pd.Timestamp.now()
    
    # Prepara o cenário: 
    # 1. Compra BTC Spot
    engine.buy_and_hodl(amount_usd=200.0, current_btc_price=50000.0, timestamp=ts)
    
    # 2. Abre LP (mocked via chamada interna, mas precisa de mock no banco se n tiver DB. 
    # Para o teste, open_lp em TDD costuma mockar o DB ou isolar)
    # Como não temos mock aqui, vamos apenas criar a LP manualmente para evitar erros de banco de dados no teste
    engine.usd_balance -= 501.0
    engine.active_lps.append({
        "id": 999, "L": 0.01, "range_lower": 40000, "range_upper": 60000, 
        "open_timestamp": ts, "entry_price": 50000.0, "initial_capital_usd": 500.0,
        "fees_accrued_usdt": 0.0, "fees_accrued_btc": 0.0,
        "initial_amount_btc": 0.005, "initial_amount_usdt": 250.0,
        "days_out_of_range": 0 
    })
    
    # 3. Adiciona colateral (simulando AAVE)
    engine.btc_collateral_balance = 0.001
    
    # Verifica estado antes do kill switch
    assert getattr(engine, 'is_killed', False) is False
    assert len(engine.active_lps) == 1
    assert engine.btc_hodl_balance > 0
    assert engine.btc_collateral_balance > 0
    
    # Executa Kill Switch
    engine.emergency_shutdown(current_price=45000.0, timestamp=ts)
    
    # Verifica estado após
    assert engine.is_killed is True
    assert len(engine.active_lps) == 0
    assert engine.btc_hodl_balance == 0.0
    assert engine.btc_collateral_balance == 0.0
    assert engine.usd_balance > 0.0 # Todo o capital voltou para USD

def test_risk_manager_drawdown_limits():
    """Testa os limites de drawdown do RiskManager."""
    rm = RiskManager(gas_reserve_usd=50.0, simulated_gas_fee_usd=1.0, 
                     max_global_drawdown=0.15, max_daily_drawdown=0.10)
    
    # HWM = 1000, Current = 950 -> Drawdown 5% (Seguro)
    assert rm.check_drawdown_limits(current_equity=950.0, global_hwm=1000.0, daily_hwm=1000.0) == 'SAFE'
    
    # HWM = 1000, Current = 890 -> Drawdown 11% (Viola Daily)
    assert rm.check_drawdown_limits(current_equity=890.0, global_hwm=1000.0, daily_hwm=1000.0) == 'KILL_SWITCH'
    
    # Global HWM = 1000, Daily HWM = 900, Current = 840. 
    # Daily DD = (900-840)/900 = 6.6% (Seguro)
    # Global DD = (1000-840)/1000 = 16% (Viola Global)
    assert rm.check_drawdown_limits(current_equity=840.0, global_hwm=1000.0, daily_hwm=900.0) == 'KILL_SWITCH'

