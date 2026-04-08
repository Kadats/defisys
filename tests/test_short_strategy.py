import pytest
import pandas as pd
from backend.src.core.trading_engine import TradingEngine
from backend.src.strategies.short_strategy import AggressiveShortStrategy

def test_aggressive_short_strategy_profit_on_drop():
    """
    Testa se a estratégia de Short gera lucro quando o preço cai.
    """
    engine = TradingEngine(initial_capital_usd=1000.0, gas_fee_usd=1.0)
    strategy = AggressiveShortStrategy()
    ts = pd.Timestamp("2025-01-01")
    
    # 1. Entrada: Preço $50,000, ML Proba 0.10 (Alta confiança na queda)
    row_entry = pd.Series({"Close": 50000.0, "prediction_proba": 0.10})
    decision_entry = strategy.execute(row_entry, engine, ts)
    
    assert decision_entry["action"] == "DIRECTIONAL_SHORT"
    assert len(engine.active_shorts) == 1
    
    initial_equity = engine._calculate_portfolio_value(50000.0)
    usd_before = engine.usd_balance
    
    # 2. Movimento: Preço cai 10% para $45,000
    ts_exit = ts + pd.Timedelta(hours=4)
    row_exit = pd.Series({"Close": 45000.0, "prediction_proba": 0.15})
    
    # A estratégia deve disparar Take Profit
    decision_exit = strategy.execute(row_exit, engine, ts_exit)
    
    assert decision_exit["action"] == "TAKE_PROFIT"
    assert len(engine.active_shorts) == 0
    
    final_equity = engine._calculate_portfolio_value(45000.0)
    
    # Validação: Equity final deve ser maior que inicial (lucro no short)
    # Lucro esperado: (50000 - 45000) * BTC_Amount
    # BTC_Amount = (Colateral / 50000) roughly.
    # Colateral = (1000 - 50) * 0.5 = 475.
    # BTC_Amount = 475 / 50000 = 0.0095.
    # Lucro = 5000 * 0.0095 = $47.5.
    # Taxas: $1 (abrir) + $1 (fechar) = $2.
    # Equity Final deve ser ~1045.5
    
    assert final_equity > initial_equity
    assert engine.usd_balance > 1000.0
    print(f"Initial Equity: {initial_equity}, Final Equity: {final_equity}")

def test_aggressive_short_strategy_stop_loss():
    """
    Testa se o Stop Loss do Short funciona quando o preço sobe.
    """
    engine = TradingEngine(initial_capital_usd=1000.0, gas_fee_usd=1.0)
    strategy = AggressiveShortStrategy()
    ts = pd.Timestamp("2025-01-01")
    
    # Entrada
    row_entry = pd.Series({"Close": 50000.0, "prediction_proba": 0.05})
    strategy.execute(row_entry, engine, ts)
    
    # Preço sobe 6% (Stop Loss é 5%)
    ts_exit = ts + pd.Timedelta(hours=4)
    row_exit = pd.Series({"Close": 53000.0, "prediction_proba": 0.10})
    
    decision_exit = strategy.execute(row_exit, engine, ts_exit)
    
    assert decision_exit["action"] == "STOP_LOSS"
    assert len(engine.active_shorts) == 0
    assert engine._calculate_portfolio_value(53000.0) < 1000.0
