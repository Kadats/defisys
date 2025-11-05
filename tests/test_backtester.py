import pytest
import pandas as pd
import math
from backend.src.backtester import Backtester, LOAN_TO_VALUE_RATIO, DEBT_INTEREST_RATE
from backend.src.strategies import run_strategy_regime_switcher, DAYS_OUT_OF_RANGE_THRESHOLD

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

@pytest.fixture
def setup_lp_magic_numbers(fresh_backtester):
    """
    Fixture que cria um backtester e abre uma LP com 
    números fáceis de calcular (Range 100-400, Aberta em 225).
    """
    bt = fresh_backtester
    bt.open_lp(
        capital_usd=1000.0,
        range_lower=100.0,
        range_upper=400.0,
        current_btc_price=225.0,
        timestamp=pd.Timestamp('2025-01-01')
    )
    lp = bt.active_lps[0]
    # L = 114.285714
    return bt, lp

def test_lp_value_price_goes_up_above_range(setup_lp_magic_numbers):
    """
    Testa o valor da LP (IL) se o preço subir ACIMA do range.
    A posição deve virar 100% USDT.
    """
    bt, lp = setup_lp_magic_numbers
    
    # Preço sobe para $500 (acima do range_upper de $400)
    new_price = 500.0 
    
    # Chamamos a função privada (pragmático para testar a matemática)
    value_usd, amount_btc, amount_usdt = bt._get_lp_value(lp, new_price)
    
    # Cálculos manuais:
    # L = 114.285714
    # sqrt_pa = 10, sqrt_pb = 20
    # amount_usdt = L * (sqrt_pb - sqrt_pa) = 114.285714 * (20 - 10) = 1142.85714
    # amount_btc = 0
    
    assert amount_btc == 0
    assert amount_usdt == pytest.approx(1142.85714)
    assert value_usd == pytest.approx(1142.85714) # Valor total é só o USDT
    
    # Compara com HODL (100% em BTC)
    # Custo inicial foi $1000 em BTC @ $225 = 4.444 BTC
    # Valor HODL = 4.444 * 500 = $2222.22
    # A LP teve $1142.85 (Impermanent Loss)

def test_lp_value_price_goes_down_below_range(setup_lp_magic_numbers):
    """
    Testa o valor da LP (IL) se o preço cair ABAIXO do range.
    A posição deve virar 100% BTC.
    """
    bt, lp = setup_lp_magic_numbers
    
    # Preço cai para $50 (abaixo do range_lower de $100)
    new_price = 50.0
    
    value_usd, amount_btc, amount_usdt = bt._get_lp_value(lp, new_price)
    
    # Cálculos manuais:
    # L = 114.285714
    # sqrt_pa = 10, sqrt_pb = 20
    # amount_btc = L * ( (1/sqrt_pa) - (1/sqrt_pb) ) 
    # amount_btc = 114.285714 * ( (1/10) - (1/20) ) = 114.285714 * (0.1 - 0.05) = 5.714285
    # amount_usdt = 0
    
    assert amount_btc == pytest.approx(5.714285714)
    assert amount_usdt == 0
    # Valor total = 5.714285 BTC * $50/BTC = $285.714
    assert value_usd == pytest.approx(285.714285714)

def test_fee_simulation_logic(setup_lp_magic_numbers):
    """
    Testa se a simulação de taxas no loop 'run' funciona.
    """
    bt, lp = setup_lp_magic_numbers
    # lp foi aberto com $1000 @ $225
    
    # Criamos um DataFrame falso com 1 linha de dados
    mock_data = {
        'Open_time': [pd.Timestamp('2025-01-02')],
        'Close': [225.0], # Preço dentro do range
        'VolumeUSD': [500_000_000.0], # Volume da pool inteira
        'TVL_USD': [1_000_000_000.0],  # TVL da pool inteira
        'SMA_50': [200.0],
        'RSI': [50.0],
        'FNG_Value': [50.0]
    }
    mock_df = pd.DataFrame(mock_data)
    
    # Executa o backtest com uma estratégia vazia
    bt.run(mock_df, strategy_function=lambda row, engine, timestamp: None)
    
    assert lp['fees_accrued_usdt'] == pytest.approx(1.5)
    assert lp['fees_accrued_btc'] == 0 # (Simplificação: acumulamos tudo em USDT)

def test_fee_simulation_outside_range(setup_lp_magic_numbers):
    """
    Testa se a simulação de taxas NÃO acumula se o preço estiver fora do range.
    """
    bt, lp = setup_lp_magic_numbers
    
    mock_data = {
        'Open_time': [pd.Timestamp('2025-01-02')],
        'Close': [500.0], # Preço FORA do range (100-400)
        'VolumeUSD': [500_000_000.0],
        'TVL_USD': [1_000_000_000.0],
        'SMA_50': [200.0],
        'RSI': [50.0],
        'FNG_Value': [50.0]
    }
    mock_df = pd.DataFrame(mock_data)
    
    bt.run(mock_df, strategy_function=lambda row, engine, timestamp: None)
    
    # Nenhuma taxa deve ser acumulada
    assert lp['fees_accrued_usdt'] == 0.0

def test_backtester_days_out_of_range_counter(fresh_backtester):
    """
    Testa se o motor do backtester incrementa 'days_out_of_range' corretamente.
    """
    bt = fresh_backtester
    bt.open_lp(1000, 100, 200, 150, pd.Timestamp('2025-01-01'))
    lp = bt.active_lps[0]
    
    # Criar 4 dias de dados: Dentro, Fora, Fora, Dentro
    mock_data = {
        'Open_time': [pd.Timestamp('2025-01-02'), pd.Timestamp('2025-01-03'), pd.Timestamp('2025-01-04'), pd.Timestamp('2025-01-05')],
        'Close': [150, 50, 55, 150], # Dentro, Fora, Fora, Dentro
        'SMA_50': [140, 60, 60, 140],
        'RSI': [50, 30, 30, 50],
        'FNG_Value': [50, 30, 30, 50],
        'VolumeUSD': [0]*4, 'TVL_USD': [1]*4 # (Irrelevante para este teste)
    }
    mock_df = pd.DataFrame(mock_data)

    # Executa o backtest (a estratégia não deve fazer nada, pois a LP está ativa)
    bt.run(mock_df, strategy_function=run_strategy_regime_switcher)
    
    # No final, o preço voltou para dentro do range, o contador deve ser 0
    assert lp['days_out_of_range'] == 0
    
    # (Para um teste mais robusto, poderíamos verificar o valor a cada passo,
    # mas o 'reset' no final já valida a lógica de incremento e reset)

def create_mock_df_aave(price: float, days: int) -> pd.DataFrame:
    """Cria um DataFrame simples para testes do AAVE loop."""
    return pd.DataFrame({
        'Open_time': pd.date_range(start='2025-01-01', periods=days),
        'Close': [price] * days,
        'SMA_50': [price] * days,
        'RSI': [50] * days,
        'FNG_Value': [50] * days,
        'VolumeUSD': [0] * days,
        'TVL_USD': [1] * days
    })

def test_aave_loop_initial_setup(fresh_backtester):
    """Testa se o setup (Ponto 1 e 2) funciona no primeiro dia do 'run'."""
    bt = fresh_backtester # Inicia com $1000 USD
    mock_df = create_mock_df_aave(price=100.0, days=1)
    
    # Rodar 1 dia com uma estratégia que não faz nada
    bt.run(mock_df, strategy_function=lambda r, e, t: None)
    
    # Ponto 1: Comprou o colateral
    assert bt.initial_capital == 1000.0
    assert bt.btc_hodl_balance == 10.0 # $1000 / $100/BTC
    
    # Ponto 2: Pegou o empréstimo
    expected_debt = 1000.0 * LOAN_TO_VALUE_RATIO # 1000 * 0.35 = 350
    assert bt.total_debt_usd == 350.0
    
    # Ponto 3: Pagou o juro de 1 dia
    daily_interest = 350.0 * (DEBT_INTEREST_RATE / 365)
    assert bt.usd_balance == pytest.approx(expected_debt - daily_interest)
    
    # Ponto 5: Cálculo do Patrimônio Líquido
    # (HODL * Preço) + (Caixa) - (Dívida)
    # (10 * 100) + (350 - juro) - (350) = 1000 - juro
    expected_net_worth = 1000.0 - daily_interest
    assert bt.portfolio_history[-1] == pytest.approx(expected_net_worth)

def test_aave_loop_daily_interest_accrual(fresh_backtester):
    """Testa se o juro (Ponto 3) é acumulado corretamente por 3 dias."""
    bt = fresh_backtester
    mock_df = create_mock_df_aave(price=100.0, days=3)
    
    bt.run(mock_df, strategy_function=lambda r, e, t: None)
    
    expected_debt = 350.0
    daily_interest = 350.0 * (DEBT_INTEREST_RATE / 365)
    total_interest_paid = daily_interest * 3 # 3 dias
    
    # O caixa deve ser o empréstimo original menos 3 dias de juros
    assert bt.usd_balance == pytest.approx(expected_debt - total_interest_paid)
    
    # O patrimônio líquido deve ser o capital inicial menos 3 dias de juros
    expected_net_worth = 1000.0 - total_interest_paid
    assert bt.portfolio_history[-1] == pytest.approx(expected_net_worth)

def test_aave_loop_strategy_opens_lp_with_loaned_capital(fresh_backtester, mocker):
    """Testa se a estratégia (Ponto 4) usa o capital emprestado."""
    bt = fresh_backtester # Inicia com $1000 USD
    
    # Simular Regime SIDEWAYS (Farm)
    mocker.patch('backend.src.strategies.analyze_market_regime', return_value='SIDEWAYS')
    mock_df = create_mock_df_aave(price=100.0, days=1)
    
    bt.run(mock_df, strategy_function=run_strategy_regime_switcher)
    
    # O setup consumiu os $1000 e deu $350 de caixa (menos juros)
    daily_interest = 350.0 * (DEBT_INTEREST_RATE / 365)
    expected_capital_to_open = 350.0 - daily_interest
    
    assert len(bt.active_lps) == 1
    lp = bt.active_lps[0]
    
    # O capital inicial da LP deve ser o caixa disponível (dinheiro do empréstimo)
    assert lp['initial_capital_usd'] == pytest.approx(expected_capital_to_open)
    # O caixa do backtester deve ter sido zerado (pois foi todo para a LP)
    assert bt.usd_balance == 0.0
    # O HODL e a Dívida não mudam
    assert bt.btc_hodl_balance == 10.0
    assert bt.total_debt_usd == 350.0

def test_aave_loop_full_net_worth_calculation(fresh_backtester, mocker):
    """Testa o cálculo do Patrimônio Líquido (Ponto 5) com todos os componentes."""
    bt = fresh_backtester
    mocker.patch('backend.src.strategies.analyze_market_regime', return_value='SIDEWAYS')
    mock_df = create_mock_df_aave(price=100.0, days=1) # Preço = $100

    # Rodar 1 dia, o que fará:
    # 1. Setup: HODL=10 BTC, Dívida=350, Caixa=350
    # 2. Pagar Juros: Caixa = 350 - juro1
    # 3. Estratégia: Abrir LP com (350 - juro1). Caixa = 0
    bt.run(mock_df, strategy_function=run_strategy_regime_switcher)
    
    # Pega o valor final do portfólio (Patrimônio Líquido)
    final_net_worth = bt.portfolio_history[-1]

    # Cálculo manual do Patrimônio Líquido:
    hodl_value = 10.0 * 100.0 # $1000
    lp_value = 350.0 - (350.0 * (DEBT_INTEREST_RATE / 365)) # Valor da LP
    cash_value = 0.0
    debt_value = 350.0
    
    expected_net_worth = (hodl_value + lp_value + cash_value) - debt_value
    # (1000) + (350 - juro) + (0) - (350) = 1000 - juro
    
    assert final_net_worth == pytest.approx(expected_net_worth)

