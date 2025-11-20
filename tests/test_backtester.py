import pytest
import pandas as pd
import math
from backend.src.backtester import (
    Backtester, 
    LOAN_TO_VALUE_RATIO, 
    DEBT_INTEREST_RATE,
    LIQUIDATION_THRESHOLD
)
from backend.src.strategies import run_strategy_regime_switcher, DAYS_OUT_OF_RANGE_THRESHOLD

@pytest.fixture
def fresh_backtester():
    """Retorna uma instância nova do Backtester com $1000 (antes do setup)."""
    return Backtester(initial_capital_usd=1000.0)

# --- 1. TESTES DE MATEMÁTICA PURA (Sem Mudanças) ---
def test_open_lp_price_below_range(fresh_backtester):
    bt = fresh_backtester
    bt.open_lp(100.0, 150.0, 200.0, 100.0, pd.Timestamp('2025-01-01'))
    assert bt.active_lps[0]['initial_amount_usdt'] == 0.0
    assert bt.active_lps[0]['initial_amount_btc'] == pytest.approx(1.0)

def test_open_lp_price_above_range(fresh_backtester):
    bt = fresh_backtester
    bt.open_lp(250.0, 150.0, 200.0, 300.0, pd.Timestamp('2025-01-01'))
    assert bt.active_lps[0]['initial_amount_usdt'] == pytest.approx(250.0)
    assert bt.active_lps[0]['initial_amount_btc'] == 0.0

def test_open_lp_price_within_range(fresh_backtester):
    bt = fresh_backtester
    bt.open_lp(1000.0, 100.0, 400.0, 225.0, pd.Timestamp('2025-01-01'))
    total_cost = bt.active_lps[0]['initial_amount_usdt'] + (bt.active_lps[0]['initial_amount_btc'] * 225.0)
    assert total_cost == pytest.approx(1000.0, rel=1e-3)

@pytest.fixture
def setup_lp_magic_numbers(fresh_backtester):
    """Fixture que cria uma LP manual para testes de matemática."""
    bt = fresh_backtester
    bt.open_lp(1000.0, 100.0, 400.0, 225.0, pd.Timestamp('2025-01-01'))
    # Garante que a LP foi criada antes de retornar
    assert len(bt.active_lps) == 1
    return bt, bt.active_lps[0]

def test_lp_value_price_goes_up_above_range(setup_lp_magic_numbers):
    bt, lp = setup_lp_magic_numbers
    value_usd, _, _ = bt._get_lp_value(lp, 500.0)
    assert value_usd == pytest.approx(1142.85714)

def test_lp_value_price_goes_down_below_range(setup_lp_magic_numbers):
    bt, lp = setup_lp_magic_numbers
    value_usd, _, _ = bt._get_lp_value(lp, 50.0)
    assert value_usd == pytest.approx(285.714285714)

def test_fee_simulation_logic(setup_lp_magic_numbers):
    bt, lp = setup_lp_magic_numbers
    mock_data = {
        'Open_time': [pd.Timestamp('2025-01-02')], 'Close': [225.0],
        'VolumeUSD': [500_000_000.0], 'TVL_USD': [1_000_000_000.0],
        'SMA_50': [200.0], 'RSI': [50.0], 'FNG_Value': [50.0]
    }
    mock_df = pd.DataFrame(mock_data)
    bt.run(mock_df, strategy_function=lambda row, engine, timestamp: None)
    assert lp['fees_accrued_usdt'] == pytest.approx(1.5)

def test_fee_simulation_outside_range(setup_lp_magic_numbers):
    bt, lp = setup_lp_magic_numbers
    mock_data = {
        'Open_time': [pd.Timestamp('2025-01-02')], 'Close': [500.0],
        'VolumeUSD': [500_000_000.0], 'TVL_USD': [1_000_000_000.0],
        'SMA_50': [200.0], 'RSI': [50.0], 'FNG_Value': [50.0]
    }
    mock_df = pd.DataFrame(mock_data)
    bt.run(mock_df, strategy_function=lambda row, engine, timestamp: None)
    assert lp['fees_accrued_usdt'] == 0.0

# --- 2. TESTES DE LÓGICA DE ESTRATÉGIA (VÁLIDOS) ---
def test_backtester_days_out_of_range_counter(fresh_backtester):
    bt = fresh_backtester
    bt.open_lp(1000, 100, 200, 150, pd.Timestamp('2025-01-01'))
    bt.usd_balance = 0 
    lp = bt.active_lps[0]
    mock_data = {
        'Open_time': pd.date_range(start='2025-01-02', periods=4),
        'Close': [150, 50, 55, 150],
        'SMA_50': [140, 60, 60, 140], 'RSI': [50, 30, 30, 50],
        'FNG_Value': [50, 30, 30, 50], 'VolumeUSD': [0]*4, 'TVL_USD': [1]*4 
    }
    mock_df = pd.DataFrame(mock_data)
    bt.run(mock_df, strategy_function=run_strategy_regime_switcher)
    assert lp['days_out_of_range'] == 0

def test_strategy_closes_lp_after_threshold(fresh_backtester, mocker):
    bt = fresh_backtester
    bt.open_lp(1000, 100, 200, 150, pd.Timestamp('2025-01-01'))
    bt.total_debt_usd = 500.0 
    bt.btc_hodl_balance = 10.0 # Adiciona colateral para não ser liquidado
    days_to_run = DAYS_OUT_OF_RANGE_THRESHOLD + 1
    mock_data = {
        'Open_time': pd.date_range(start='2025-01-02', periods=days_to_run),
        'Close': [50] * days_to_run,
        'SMA_50': [60] * days_to_run, 'RSI': [30] * days_to_run,
        'FNG_Value': [30] * days_to_run, 'VolumeUSD': [0]*days_to_run, 'TVL_USD': [1]*days_to_run
    }
    mock_df = pd.DataFrame(mock_data)
    bt.run(mock_df, strategy_function=run_strategy_regime_switcher)
    assert len(bt.active_lps) == 0

# --- 3. NOVOS TESTES (AAVE LOOP) ---
def create_mock_df_for_strategy(regime: str, price: float, sma_50: float, rsi: float, fng: float, days: int) -> pd.DataFrame:
    """Cria um DataFrame completo para simular a estratégia."""
    return pd.DataFrame({
        'Open_time': pd.date_range(start='2025-01-01', periods=days),
        'Close': [price] * days, 'SMA_50': [sma_50] * days, 'RSI': [rsi] * days,
        'FNG_Value': [fng] * days, 'VolumeUSD': [0] * days, 'TVL_USD': [1] * days
    })

def test_strategy_stays_in_usd_before_first_signal(fresh_backtester, mocker):
    """Testa se o bot fica 100% em USD se o sinal de compra (BEARISH) nunca vier."""
    bt = fresh_backtester 
    mocker.patch('backend.src.regime_analyzer.analyze_market_regime', return_value='SIDEWAYS')
    mock_df = create_mock_df_for_strategy('SIDEWAYS', 100, 100, 50, 50, 5)
    bt.run(mock_df, strategy_function=run_strategy_regime_switcher)
    assert bt.btc_hodl_balance == 0.0 
    assert bt.total_debt_usd == 0.0   
    assert len(bt.active_lps) == 0    
    assert bt.usd_balance == 1000.0   
    assert bt.portfolio_history[-1] == 1000.0 

def test_strategy_executes_full_recursive_loop_on_first_bearish_signal(fresh_backtester, mocker):
    """Testa se a cascata 'BEARISH' (comprar colateral, emprestar, loop) é executada corretamente."""
    bt = fresh_backtester 
    mocker.patch('backend.src.regime_analyzer.analyze_market_regime', return_value='BEARISH')
    mock_df = create_mock_df_for_strategy('BEARISH', price=100.0, sma_50=110, rsi=30, fng=30, days=1)
    bt.run(mock_df, strategy_function=run_strategy_regime_switcher)
    
    daily_interest = 500.0 * (DEBT_INTEREST_RATE / 365)
    
    assert bt.total_debt_usd == 500.0
    assert bt.btc_hodl_balance == 12.5 
    assert len(bt.active_lps) == 1
    
    lp = bt.active_lps[0]
    lp_capital_usd = 2.5 * 100.0 
    assert lp['initial_capital_usd'] == pytest.approx(lp_capital_usd)
    assert lp['range_lower'] == 100 * 0.70 
    
    # --- CORREÇÃO DO BUG (Falha 1) ---
    # O juro do Dia 1 só é pago no Dia 2. No fim do Dia 1, o balanço deve ser 0.
    assert bt.usd_balance == pytest.approx(0.0) 
    
    # O Patrimônio Líquido é (HODL + LP + Caixa) - Dívida
    # (12.5*100) + 250 + 0 - 500 = 1250 + 250 - 500 = 1000.0
    # O juro ainda não foi pago, então o patrimônio líquido no fim do Dia 1 é 1000.
    expected_net_worth = 1000.0
    assert bt.portfolio_history[-1] == pytest.approx(expected_net_worth)

def test_strategy_opens_new_lp_post_loop(fresh_backtester, mocker):
    """Testa se a estratégia abre uma LP 'SIDEWAYS' (Farm) se já estivermos alavancados."""
    bt = fresh_backtester
    
    # --- CORREÇÃO DO BUG (Falha 2): Adicionar colateral ---
    bt.btc_hodl_balance = 10.0 
    bt.total_debt_usd = 500.0  
    bt.usd_balance = 100.0     

    mocker.patch('backend.src.regime_analyzer.analyze_market_regime', return_value='SIDEWAYS')
    mock_df = create_mock_df_for_strategy('SIDEWAYS', price=150.0, sma_50=140, rsi=50, fng=50, days=1)
    
    bt.run(mock_df, strategy_function=run_strategy_regime_switcher)
    
    assert len(bt.active_lps) == 1
    lp = bt.active_lps[0]
    
    daily_interest = 500.0 * (DEBT_INTEREST_RATE / 365)
    # O capital da LP será o caixa (100) - os juros (0.10)
    expected_capital = 100.0 - daily_interest 
    
    assert lp['initial_capital_usd'] == pytest.approx(expected_capital)
    assert lp['range_lower'] == 150.0 * 0.85 
    # O balanço final de USD será 0 (pois foi todo para a LP)
    assert bt.usd_balance == 0.0

def test_backtester_pays_daily_interest_if_debt_exists(fresh_backtester, mocker):
    """Testa se o juro é pago corretamente sem abrir LPs."""
    bt = fresh_backtester
    bt.btc_hodl_balance = 25.0   # Increased to maintain HF > 1.5 with rebalance logic
    bt.total_debt_usd = 500.0
    bt.usd_balance = 100.0
    
    # Use a no-op strategy to avoid LP opening
    def noop_strategy(row, engine, timestamp):
        pass
    
    mock_df = create_mock_df_for_strategy('BULL_TOP', price=200, sma_50=150, rsi=80, fng=80, days=3)

    bt.run(mock_df, strategy_function=noop_strategy)
    
    daily_interest = 500.0 * (DEBT_INTEREST_RATE / 365)
    total_interest_paid = daily_interest * 3
    
    # With no-op strategy and sufficient collateral, only interest should be deducted
    assert bt.usd_balance == pytest.approx(100.0 - total_interest_paid, rel=1e-6)

def test_backtester_handles_liquidation_correctly(fresh_backtester, mocker):
    """Testa se o backtester é liquidado (HF <= 1.0) e zera o portfólio."""
    bt = fresh_backtester
    
    bt.btc_hodl_balance = 10.0
    bt.total_debt_usd = 800.0
    bt.usd_balance = 0.0
    
    # HF = (10 * Preço * 0.8) / 800
    # Se Preço = 99, HF < 1.0
    mock_df = create_mock_df_for_strategy('BEARISH', price=99.0, sma_50=110, rsi=30, fng=30, days=1)
    
    bt.run(mock_df, strategy_function=run_strategy_regime_switcher)
    
    assert bt.is_liquidated == True
    assert bt.btc_hodl_balance == 0.0
    assert bt.total_debt_usd == 0.0
    assert len(bt.active_lps) == 0
    assert bt.portfolio_history[-1] == 0.0

