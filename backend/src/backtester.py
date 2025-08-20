# backend/src/backtester.py

import pandas as pd
from .strategies import generate_signals

def run_backtest(df: pd.DataFrame, initial_capital_usd: float = 1000) -> dict:
    """
    Executa um backtest de uma estratégia de acumulação de Bitcoin via gestão de pools de liquidez concentrada.

    Args:
        df (pd.DataFrame): DataFrame contendo os dados OHLCV e os indicadores.
        initial_capital_usd (float): Capital inicial em USD para o backtest.

    Returns:
        dict: Um dicionário com os resultados e métricas do backtest.
    """
    if df.empty:
        print("Erro: DataFrame vazio para backtest.")
        return {}

    df_with_signals = generate_signals(df)

    usd_amount = initial_capital_usd
    btc_amount = 0.0
    position_is_open = False
    
    lp_usd_initial = 0.0
    lp_btc_initial = 0.0
    fees_accrued_usd = 0.0
    
    initial_btc_price = df_with_signals.iloc[0]['Close']
    
    for index, row in df_with_signals.iterrows():
        close_price = row['Close']
        signal = row['Signal']
        
        if signal == 'ENTRAR EM POOL' and not position_is_open:
            lp_range_lower = row['Pool_Range_Lower']
            lp_range_upper = row['Pool_Range_Upper']
            
            usd_to_pool = usd_amount / 2
            btc_to_pool = (usd_amount / 2) / close_price
            
            lp_usd_initial = usd_to_pool
            lp_btc_initial = btc_to_pool
            usd_amount = 0.0
            btc_amount = 0.0
            position_is_open = True
            print(f"[{row['Open_time']}] SINAL DE ENTRADA NA POOL: Capital dividido em BTC e USD. Range: ${lp_range_lower:.2f} a ${lp_range_upper:.2f}")

        elif signal == 'SAIR DA POOL' and position_is_open:
            current_lp_value = lp_usd_initial + (lp_btc_initial * close_price)
            buy_and_hold_value = (initial_capital_usd / initial_btc_price) * close_price
            impermanent_loss = current_lp_value - buy_and_hold_value
            
            days_in_pool = 1
            fees_earned = (current_lp_value * 0.003) * days_in_pool
            fees_accrued_usd += fees_earned

            usd_amount = current_lp_value + fees_earned
            
            lp_usd_initial = 0.0
            lp_btc_initial = 0.0
            position_is_open = False
            print(f"[{row['Open_time']}] SINAL DE SAÍDA DA POOL: Posição encerrada. Valor final: ${usd_amount:.2f} (IL: ${impermanent_loss:.2f}, Fees: ${fees_earned:.2f})")

    final_btc_price = df_with_signals.iloc[-1]['Close']
    
    if position_is_open:
        final_usd_value = lp_usd_initial + (lp_btc_initial * final_btc_price) + fees_accrued_usd
    else:
        final_usd_value = usd_amount
    
    btc_benchmark_final_value = (initial_capital_usd / initial_btc_price) * final_btc_price
    
    profit_usd = final_usd_value - initial_capital_usd
    profit_percentage_usd = (profit_usd / initial_capital_usd) * 100
    
    btc_benchmark_profit_usd = btc_benchmark_final_value - initial_capital_usd
    btc_benchmark_profit_percentage = (btc_benchmark_profit_usd / initial_capital_usd) * 100

    results = {
        'initial_capital_usd': initial_capital_usd,
        'final_usd_value': final_usd_value,
        'profit_usd': profit_usd,
        'profit_percentage_usd': profit_percentage_usd,
        'btc_benchmark_profit_percentage': btc_benchmark_profit_percentage,
    }

    return results

