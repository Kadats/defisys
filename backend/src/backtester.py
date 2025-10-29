# Em backend/src/backtester.py
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class Backtester:
    """
    Motor de backtest genérico baseado em eventos.

    Este motor não contém nenhuma lógica de estratégia. Em vez disso, ele
    aceita uma 'strategy_function' que é chamada a cada passo (vela)
    e pode tomar decisões de portfólio.
    """
    
    def __init__(self, initial_capital_usd: float = 1000.0):
        # Estado do Portfólio
        self.initial_capital = initial_capital_usd
        self.usd_balance = initial_capital_usd
        self.btc_hodl_balance = 0.0
        self.active_lps = [] # Lista para guardar as posições de LP ativas
        
        # Rastreamento
        self.portfolio_history = [] # Guarda o valor total do portfólio a cada passo
        self.decision_history = []  # Guarda todas as ações tomadas
        
        logger.info(f"Backtester v2 (Engine) inicializado com ${initial_capital_usd} USD.")

    def _calculate_portfolio_value(self, current_btc_price: float) -> float:
        """Calcula o valor total do portfólio em USD."""
        # Valor das LPs ativas (Esta é a parte mais complexa que vamos construir)
        lp_value = 0.0
        for lp in self.active_lps:
            # TODO: Implementar cálculo de valor da LP (taxas + IL)
            # Por agora, vamos usar uma aproximação simples
            hodl_value = lp['initial_capital'] * (current_btc_price / lp['entry_price'])
            lp_value += hodl_value # Simplificação temporária
            
        # Valor do BTC em HODL
        hodl_value = self.btc_hodl_balance * current_btc_price
        
        return self.usd_balance + hodl_value + lp_value

    # --- API PÚBLICA (Funções que a Estratégia pode chamar) ---

    def buy_and_hodl(self, amount_usd: float, current_btc_price: float):
        """Aloca capital de USD para a carteira HODL de BTC."""
        if self.usd_balance < amount_usd:
            logger.warning("Capital insuficiente para comprar HODL.")
            return
            
        btc_bought = amount_usd / current_btc_price
        self.usd_balance -= amount_usd
        self.btc_hodl_balance += btc_bought
        self.decision_history.append(f"HODL BUY: {btc_bought:.6f} BTC @ ${current_btc_price}")

    def open_lp(self, capital_usd: float, range_lower: float, range_upper: float, current_btc_price: float, timestamp):
        """Abre uma nova posição de LP."""
        if self.usd_balance < capital_usd:
            logger.warning("Capital insuficiente para abrir LP.")
            return

        self.usd_balance -= capital_usd
        new_lp = {
            "id": len(self.active_lps) + 1,
            "entry_price": current_btc_price,
            "initial_capital": capital_usd,
            "range_lower": range_lower,
            "range_upper": range_upper,
            "fees_accrued": 0.0,
            "open_timestamp": timestamp
        }
        self.active_lps.append(new_lp)
        self.decision_history.append(f"OPEN LP: ${capital_usd} @ ${current_btc_price} | Range: ${range_lower:.2f}-${range_upper:.2f}")

    def close_lp(self, lp_id: int, current_btc_price: float):
        """Fecha uma posição de LP e retorna o valor para o balanço de USD."""
        lp_to_close = next((lp for lp in self.active_lps if lp['id'] == lp_id), None)
        if not lp_to_close:
            logger.warning(f"Tentativa de fechar LP ID {lp_id} inexistente.")
            return

        # TODO: Cálculo de valor real (com IL e taxas)
        # Por agora, aproximação simples
        hodl_value = lp_to_close['initial_capital'] * (current_btc_price / lp_to_close['entry_price'])
        final_value = hodl_value + lp_to_close['fees_accrued']

        self.usd_balance += final_value
        self.active_lps.remove(lp_to_close)
        self.decision_history.append(f"CLOSE LP {lp_id}: Valor retornado ${final_value:.2f} @ ${current_btc_price}")

    # --- O Ponto de Entrada Principal ---
    
    def run(self, df: pd.DataFrame, strategy_function) -> dict:
        """
        Executa o backtest iterando pelo DataFrame e chamando a
        função de estratégia a cada passo.
        """
        if df.empty:
            logger.error("DataFrame vazio. Abortando backtest.")
            return {}

        logger.info(f"Iniciando Backtester v2. Processando {len(df)} velas...")

        for index, row in df.iterrows():
            current_price = row['Close']
            
            # --- 1. Atualizar Estado das Posições (Ex: Acumular taxas) ---
            # (Manteremos simples por agora)
            for lp in self.active_lps:
                if lp['range_lower'] < current_price < lp['range_upper']:
                    # Simulação de taxa diária simples
                    lp['fees_accrued'] += lp['initial_capital'] * 0.001 # 0.1% ao dia

            # --- 2. Chamar a Estratégia ---
            # A estratégia recebe a 'row' (com todos os indicadores)
            # e o 'self' (o próprio backtester, para poder chamar .open_lp(), etc.)
            strategy_function(row, self)

            # --- 3. Registrar o Valor do Portfólio ---
            total_value = self._calculate_portfolio_value(current_price)
            self.portfolio_history.append(total_value)

        # --- Fim do Backtest ---
        final_portfolio_value = self.portfolio_history[-1]
        
        # Calcular HODL benchmark
        initial_btc_price = df.iloc[0]['Close']
        hodl_btc_amount = self.initial_capital / initial_btc_price
        hodl_final_value = hodl_btc_amount * df.iloc[-1]['Close']
        
        logger.info("Backtest v2 Concluído. Valor Final: $%.2f", final_portfolio_value)

        return {
            'initial_capital_usd': self.initial_capital,
            'final_usd_value': final_portfolio_value,
            'profit_usd': final_portfolio_value - self.initial_capital,
            'profit_percentage_usd': ((final_portfolio_value / self.initial_capital) - 1) * 100,
            'btc_benchmark_final_value': hodl_final_value,
            'btc_benchmark_profit_percentage': ((hodl_final_value / self.initial_capital) - 1) * 100,
            'decision_history': self.decision_history,
        }