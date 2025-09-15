import pandas as pd
import numpy as np
import logging
from .strategies import decide_liquidity

logger = logging.getLogger(__name__)

def calculate_impermanent_loss(initial_price, current_price):
    """
    Calcula uma aproximação da Perda Impermanente (IL) sem depender do range.
    Retorna o multiplicador do valor do HODL (ex: 0.95 para uma perda de 5%).
    """
    price_ratio = current_price / initial_price
    il_multiplier = (2 * np.sqrt(price_ratio)) / (1 + price_ratio)
    return il_multiplier

def run_backtest(df: pd.DataFrame, initial_capital_usd: float = 1000, daily_fee_rate: float = 0.001) -> dict:
    """
    Executa um backtest alinhado com a lógica simples do blueprint: uma única posição gerenciada.
    """
    if df.empty or 'Oportunidade_Score' not in df.columns or df['Oportunidade_Score'].isnull().all():
        logger.error("Erro: DataFrame vazio ou indicadores compostos ausentes para o backtest.")
        return {}

    df['Decision'] = decide_liquidity(df, sentiment_col='Sentimento_Score', volatility_col='Volatilidade_Score', opportunity_col='Oportunidade_Score')

    # --- Variáveis de Estado Simplificadas ---
    capital_usd = initial_capital_usd
    position_is_open = False
    current_position = {} # Dicionário para guardar os dados da única posição ativa
    decision_history = []
    
    initial_btc_price = df.iloc[0]['Close']
    hodl_btc_amount = initial_capital_usd / initial_btc_price
    portfolio_history = []

    logger.info("--- INICIANDO BACKTEST (LÓGICA DO BLUEPRINT) ---")
    logger.info("Capital Inicial: $%0.2f USDT", capital_usd)

    for index, row in df.iterrows():
        current_price = row['Close']
        decision = row['Decision']
        last_decision = df.loc[index-1, 'Decision'] if index > 0 else 'reduzir'

        # --- LÓGICA DE GESTÃO DA POSIÇÃO ÚNICA ---

        # 1. Se a decisão for REDUZIR, fechar qualquer posição aberta.
        if decision == 'reduzir' and position_is_open:
            hodl_value = current_position['initial_capital'] * (current_price / current_position['entry_price'])
            il_multiplier = calculate_impermanent_loss(current_position['entry_price'], current_price)
            final_lp_value = (hodl_value * il_multiplier) + current_position['fees_accrued']
            
            logger.info("[%s] SAÍDA DA POOL: Preço: $%0.2f. Valor retornado: $%0.2f", row['Open_time'].date(), current_price, final_lp_value)
            
            capital_usd = final_lp_value
            position_is_open = False
            current_position = {}
            decision_history.append({
                'Data': str(row['Open_time'].date()),
                'Decisão': 'SAÍDA',
                'Tipo': 'reduzir',
                'Preço': float(current_price),
                'Capital': float(capital_usd),
                'Range': None
            })

        # 2. Se a decisão for ENTRAR (e a posição estiver fechada), abrir uma nova.
        elif decision in ['range_curto', 'range_largo'] and not position_is_open:
            position_is_open = True
            atr_multiplier = 0.75 if decision == 'range_curto' else 2.0 # Ajustando multiplicadores
            range_width = row['ATR'] * atr_multiplier
            
            current_position = {
                'type': decision,
                'initial_capital': capital_usd,
                'entry_price': current_price,
                'range_lower': current_price - range_width,
                'range_upper': current_price + range_width,
                'fees_accrued': 0.0,
            }
            logger.info("[%s] ENTRADA (%s): Capital: $%0.2f. Range: $%0.2f a $%0.2f", row['Open_time'].date(), decision.upper(), capital_usd, current_position['range_lower'], current_position['range_upper'])
            capital_usd = 0.0 # Capital está na pool
            decision_history.append({
                'Data': str(row['Open_time'].date()),
                'Decisão': 'ENTRADA',
                'Tipo': decision,
                'Preço': float(current_price),
                'Capital': float(current_position['initial_capital']),
                'Range': f"{current_position['range_lower']:.2f} - {current_position['range_upper']:.2f}"
            })

        # 3. Se a decisão MUDAR (ex: de curto para largo), ajustar o range.
        elif decision in ['range_curto', 'range_largo'] and position_is_open and decision != current_position['type']:
            # Primeiro, fecha a posição antiga
            hodl_value = current_position['initial_capital'] * (current_price / current_position['entry_price'])
            il_multiplier = calculate_impermanent_loss(current_position['entry_price'], current_price)
            capital_temp = (hodl_value * il_multiplier) + current_position['fees_accrued']
            logger.info("[%s] AJUSTE DE RANGE: Posição '%s' fechada com $%0.2f.", row['Open_time'].date(), current_position['type'], capital_temp)
            decision_history.append({
                'Data': str(row['Open_time'].date()),
                'Decisão': 'AJUSTE_DE_RANGE',
                'Tipo': current_position['type'],
                'Preço': float(current_price),
                'Capital': float(capital_temp),
                'Range': f"{current_position['range_lower']:.2f} - {current_position['range_upper']:.2f}"
            })
            
            # Reabre a nova posição com o capital atualizado
            atr_multiplier = 0.75 if decision == 'range_curto' else 2.0
            range_width = row['ATR'] * atr_multiplier
            current_position = {
                'type': decision,
                'initial_capital': capital_temp,
                'entry_price': current_price,
                'range_lower': current_price - range_width,
                'range_upper': current_price + range_width,
                'fees_accrued': 0.0,
            }
            logger.info("[%s] RE-ENTRADA (%s): Capital: $%0.2f. Novo Range: $%0.2f a $%0.2f", row['Open_time'].date(), decision.upper(), capital_temp, current_position['range_lower'], current_position['range_upper'])
            decision_history.append({
                'Data': str(row['Open_time'].date()),
                'Decisão': 'ENTRADA',
                'Tipo': decision,
                'Preço': float(current_price),
                'Capital': float(capital_temp),
                'Range': f"{current_position['range_lower']:.2f} - {current_position['range_upper']:.2f}"
            })

        # --- CÁLCULO DIÁRIO DE TAXAS E VALOR DO PORTFÓLIO ---
        if position_is_open:
            if current_position['range_lower'] < current_price < current_position['range_upper']:
                daily_fees = current_position['initial_capital'] * daily_fee_rate
                current_position['fees_accrued'] += daily_fees
            
            hodl_value = current_position['initial_capital'] * (current_price / current_position['entry_price'])
            il_multiplier = calculate_impermanent_loss(current_position['entry_price'], current_price)
            current_portfolio_value = (hodl_value * il_multiplier) + current_position['fees_accrued']
        else:
            current_portfolio_value = capital_usd
            
        portfolio_history.append(current_portfolio_value)

    # --- Finalização e Métricas ---
    df['Portfolio_Value'] = portfolio_history
    final_portfolio_value = df['Portfolio_Value'].iloc[-1]
    hodl_final_value = hodl_btc_amount * df.iloc[-1]['Close']

    profit_usd = final_portfolio_value - initial_capital_usd
    profit_percentage = (profit_usd / initial_capital_usd) * 100
    hodl_profit_percentage = ((hodl_final_value - initial_capital_usd) / initial_capital_usd) * 100

    results = {
        'initial_capital_usd': initial_capital_usd,
        'final_usd_value': final_portfolio_value,
        'profit_usd': profit_usd,
        'profit_percentage_usd': profit_percentage,
        'btc_benchmark_profit_percentage': hodl_profit_percentage,
    }
    # Inclui histórico de decisões para o dashboard
    results['decision_history'] = decision_history
    return results

