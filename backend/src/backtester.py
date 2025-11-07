import pandas as pd
import numpy as np
import math
import logging

logger = logging.getLogger(__name__)

POOL_FEE_RATE = 0.003 
LOAN_TO_VALUE_RATIO = 0.50 
DEBT_INTEREST_RATE = 0.075 
LIQUIDATION_THRESHOLD = 0.80 
LIQUIDATION_PENALTY = 0.10 

class Backtester:
    
    def __init__(self, initial_capital_usd: float = 1000.0):
        self.initial_capital = initial_capital_usd
        self.usd_balance = initial_capital_usd 
        self.btc_hodl_balance = 0.0           
        self.total_debt_usd = 0.0             
        self.loan_apy = DEBT_INTEREST_RATE
        
        self.health_factor = 999.0
        self.is_liquidated = False
        
        self.active_lps = []
        self.portfolio_history = []
        self.decision_history = []
        
        logger.info(f"Backtester v2 (Market Timing Loop) inicializado com ${initial_capital_usd} USD.")

    def _get_lp_value(self, lp: dict, current_btc_price: float) -> tuple:
        L = lp['L']; pa = lp['range_lower']; pb = lp['range_upper']; pc = current_btc_price
        sqrt_pa = math.sqrt(pa); sqrt_pb = math.sqrt(pb); sqrt_pc = math.sqrt(pc)
        amount_btc = 0; amount_usdt = 0
        if pc <= pa: amount_btc = L * ((1/sqrt_pa) - (1/sqrt_pb))
        elif pc >= pb: amount_usdt = L * (sqrt_pb - sqrt_pa)
        else:
            amount_btc = L * ((1/sqrt_pc) - (1/sqrt_pb))
            amount_usdt = L * (sqrt_pc - sqrt_pa)
        return (amount_btc * pc) + amount_usdt, amount_btc, amount_usdt

    def _calculate_portfolio_value(self, current_btc_price: float) -> float:
        if self.is_liquidated:
            return 0.0

        lp_total_value = 0.0
        for lp in self.active_lps:
            asset_value, _, _ = self._get_lp_value(lp, current_btc_price)
            fees_value = lp['fees_accrued_usdt'] + (lp['fees_accrued_btc'] * current_btc_price)
            lp_total_value += asset_value + fees_value
            
        hodl_value = self.btc_hodl_balance * current_btc_price
        cash_value = self.usd_balance
        debt_value = self.total_debt_usd
        
        net_value = (hodl_value + lp_total_value + cash_value) - debt_value
        return net_value

    def buy_and_hodl(self, amount_usd: float, current_btc_price: float):
        """Aloca capital de USD para a carteira HODL de BTC."""
        if self.usd_balance < amount_usd:
            logger.warning("Capital insuficiente para comprar HODL.")
            return
            
        btc_bought = amount_usd / current_btc_price
        self.usd_balance -= amount_usd
        self.btc_hodl_balance += btc_bought
        self.decision_history.append(f"HODL BUY: {btc_bought:.6f} BTC @ ${current_btc_price}")

    def add_collateral(self, btc_amount: float):
        """Adiciona BTC ao balanço de colateral HODL."""
        self.btc_hodl_balance += btc_amount

    def open_lp(self, capital_usd: float, range_lower: float, range_upper: float, current_btc_price: float, timestamp):
        """Abre uma nova posição de LP com matemática da Uniswap v3."""
    
        if range_lower >= range_upper:
            logger.warning(f"[{timestamp.date()}] Range inválido: Preço mínimo ${range_lower:.2f} é maior ou igual ao máximo ${range_upper:.2f}")
            return

        pa = range_lower; pb = range_upper; pc = current_btc_price
        sqrt_pa = math.sqrt(pa); sqrt_pb = math.sqrt(pb); sqrt_pc = math.sqrt(pc)
        amount_btc = 0; amount_usdt = 0; L = 0

        if pc <= pa:
            if (sqrt_pb - sqrt_pa) == 0: return
            L = ( (capital_usd / pc) * sqrt_pa * sqrt_pb ) / (sqrt_pb - sqrt_pa)
            amount_btc = capital_usd / pc
        elif pc >= pb:
            if (sqrt_pb - sqrt_pa) == 0: return
            L = capital_usd / (sqrt_pb - sqrt_pa)
            amount_usdt = capital_usd
        else:
            denominator = (2*sqrt_pc - sqrt_pa - (pc / sqrt_pb))
            if denominator == 0: return
            L = capital_usd / denominator
            amount_usdt = L * (sqrt_pc - sqrt_pa)
            amount_btc = L * ( (1/sqrt_pc) - (1/sqrt_pb) )

        # --- CORREÇÃO DA INDENTAÇÃO AQUI ---
        # Este bloco inteiro estava alinhado incorretamente.
        new_lp = {
            "id": len(self.active_lps) + 1, "L": L, "range_lower": range_lower,
            "range_upper": range_upper, "open_timestamp": timestamp,
            "entry_price": current_btc_price, "initial_capital_usd": capital_usd,
            "fees_accrued_usdt": 0.0, "fees_accrued_btc": 0.0,
            "initial_amount_btc": amount_btc, "initial_amount_usdt": amount_usdt,
            "days_out_of_range": 0 
        }
        self.active_lps.append(new_lp)
        self.decision_history.append(
            f"[{timestamp.date()}] OPEN LP: ${capital_usd:.2f} @ ${current_btc_price:.2f} | "
            f"Range: ${range_lower:.2f}-${range_upper:.2f} | "
            f"Assets: {amount_btc:.6f} BTC + {amount_usdt:.2f} USDT"
        )
        # --- FIM DA CORREÇÃO DE INDENTAÇÃO ---

    def close_lp(self, lp_id: int, current_btc_price: float, timestamp):
        lp_to_close = next((lp for lp in self.active_lps if lp['id'] == lp_id), None)
        if not lp_to_close:
            logger.warning(f"Tentativa de fechar LP ID {lp_id} inexistente.")
            return

        asset_value, _, _ = self._get_lp_value(lp_to_close, current_btc_price)
        fees_value = lp_to_close['fees_accrued_usdt'] + (lp_to_close['fees_accrued_btc'] * current_btc_price)
        final_value = asset_value + fees_value

        self.usd_balance += final_value
        self.active_lps.remove(lp_to_close)
        self.decision_history.append(
            f"[{timestamp.date()}] CLOSE LP {lp_id}: Valor retornado ${final_value:.2f} @ ${current_btc_price:.2f} "
            f"(Ativos: ${asset_value:.2f}, Taxas: ${fees_value:.2f})"
        )

    def _handle_liquidation(self, timestamp):
        """Zera o portfólio em caso de liquidação."""
        logger.error(
            f"[{timestamp.date()}] !!! LIQUIDAÇÃO !!! "
            f"Health Factor <= 1.0. Dívida: ${self.total_debt_usd:.2f}. "
            f"Colateral: {self.btc_hodl_balance:.6f} BTC. "
            "Todo o colateral foi perdido."
        )
        self.is_liquidated = True
        self.btc_hodl_balance = 0.0
        self.total_debt_usd = 0.0 
        self.usd_balance = 0.0
        self.active_lps.clear()
        self.decision_history.append(f"[{timestamp.date()}] !!! LIQUIDAÇÃO TOTAL !!!")


    def run(self, df: pd.DataFrame, strategy_function):
        if df.empty:
            logger.error("DataFrame vazio. Abortando backtest.")
            return {}

        logger.info(f"Iniciando Backtester v2 (Market Timing Loop). Processando {len(df)} velas...")
        
        for index, row in df.iterrows():
            if self.is_liquidated:
                self.portfolio_history.append(0.0)
                continue

            current_price = row['Close']
            timestamp = row['Open_time']
            
            # 1. Calcular HF e checar Liquidação (se houver dívida)
            if self.total_debt_usd > 0:
                collateral_value = self.btc_hodl_balance * current_price
                self.health_factor = (collateral_value * LIQUIDATION_THRESHOLD) / self.total_debt_usd if self.total_debt_usd > 0 else 999.0
                
                if self.health_factor <= 1.0:
                    self._handle_liquidation(timestamp)
                    self.portfolio_history.append(0.0)
                    continue 
            else:
                self.health_factor = 999.0

            # --- MUDANÇA: Bloco movido para ANTES da estratégia ---
            # 2. Pagar Juros (se houver dívida)
            if self.total_debt_usd > 0:
                daily_interest_rate = (self.loan_apy / 365)
                interest_cost = self.total_debt_usd * daily_interest_rate
                self.usd_balance -= interest_cost # Paga juros do caixa ANTES da estratégia rodar
            
            # 3. Atualizar estado das LPs
            for lp in self.active_lps:
                is_in_range = lp['range_lower'] < current_price < lp['range_upper']
                if is_in_range:
                    # ... (lógica de cálculo de taxas) ...
                    total_pool_volume_24h = row.get('VolumeUSD', 0)
                    total_pool_tvl_usd = row.get('TVL_USD', 1) 
                    if total_pool_tvl_usd > 0 and total_pool_volume_24h > 0:
                        my_lp_value_usd, _, _ = self._get_lp_value(lp, current_price)
                        my_share_of_pool = my_lp_value_usd / total_pool_tvl_usd
                        total_fees_generated_usd = total_pool_volume_24h * POOL_FEE_RATE
                        fees_earned_today_usd = total_fees_generated_usd * my_share_of_pool
                        lp['fees_accrued_usdt'] += fees_earned_today_usd
                    lp['days_out_of_range'] = 0 
                else:
                    lp['days_out_of_range'] += 1

            # 4. Chamar a Estratégia
            # (A estratégia agora verá o self.usd_balance já com os juros descontados)
            strategy_function(row, self, timestamp)
            
            # 5. Registrar o Valor do Portfólio
            total_net_value = self._calculate_portfolio_value(current_price)
            self.portfolio_history.append(total_net_value)

        # --- Fim do Backtest ---
        # ... (resto da função permanece o mesmo) ...
        final_portfolio_value = self.portfolio_history[-1] if self.portfolio_history else self.initial_capital
        
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
            'btc_benchmark_profit_percentage': ((final_portfolio_value / self.initial_capital) - 1) * 100,
            'decision_history': self.decision_history,
        }

