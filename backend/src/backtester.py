# Em backend/src/backtester.py
import pandas as pd
import numpy as np
import math  # <-- MUDANÇA 1: Adicionar import
import logging

logger = logging.getLogger(__name__)

# Taxa da pool que estamos simulando (0.3% para WETH/USDT ou WBTC/USDT)
POOL_FEE_RATE = 0.003

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

    def _get_lp_value(self, lp: dict, current_btc_price: float) -> tuple:
        """
        Calcula o valor atual dos ativos (BTC e USDT) em uma LP.
        Esta é a matemática central do Impermanent Loss.
        Retorna (valor_total_usd, amount_btc, amount_usdt)
        """
        L = lp['L']
        pa = lp['range_lower']
        pb = lp['range_upper']
        pc = current_btc_price
        
        sqrt_pa = math.sqrt(pa)
        sqrt_pb = math.sqrt(pb)
        sqrt_pc = math.sqrt(pc)

        amount_btc = 0
        amount_usdt = 0

        if pc <= pa:
            # Preço abaixo do range -> 100% BTC
            amount_btc = L * ((1/sqrt_pa) - (1/sqrt_pb))
            amount_usdt = 0
        elif pc >= pb:
            # Preço acima do range -> 100% USDT
            amount_btc = 0
            amount_usdt = L * (sqrt_pb - sqrt_pa)
        else:
            # Preço dentro do range -> Mix de BTC e USDT
            amount_btc = L * ((1/sqrt_pc) - (1/sqrt_pb))
            amount_usdt = L * (sqrt_pc - sqrt_pa)
            
        value_usd = (amount_btc * pc) + amount_usdt
        return value_usd, amount_btc, amount_usdt

    def _calculate_portfolio_value(self, current_btc_price: float) -> float:
        """Calcula o valor total do portfólio em USD."""
        
        # Valor das LPs ativas
        lp_total_value = 0.0
        for lp in self.active_lps:
            # Pega o valor dos ativos (considerando IL)
            asset_value, _, _ = self._get_lp_value(lp, current_btc_price)
            
            # Adiciona as taxas acumuladas
            fees_value = lp['fees_accrued_usdt'] + (lp['fees_accrued_btc'] * current_btc_price)
            
            lp_total_value += asset_value + fees_value
            
        # Valor do BTC em HODL
        hodl_value = self.btc_hodl_balance * current_btc_price
        
        return self.usd_balance + hodl_value + lp_total_value

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

    # --- MUDANÇA 2: Função open_lp substituída ---
    def open_lp(self, capital_usd: float, range_lower: float, range_upper: float, current_btc_price: float, timestamp):
        """
        Abre uma nova posição de LP com matemática da Uniswap v3.
        Calcula L, amount_btc e amount_usdt com base no capital e no range.
        """
        if self.usd_balance < capital_usd:
            logger.warning(f"[{timestamp.date()}] Capital insuficiente para abrir LP. Necessário: ${capital_usd:.2f}, Disponível: ${self.usd_balance:.2f}")
            return
        
        if range_lower >= range_upper:
            logger.warning(f"[{timestamp.date()}] Range inválido: Preço mínimo ${range_lower:.2f} é maior ou igual ao máximo ${range_upper:.2f}")
            return

        # 1. Cálculos de Preço (sqrt)
        pa = range_lower
        pb = range_upper
        pc = current_btc_price
        sqrt_pa = math.sqrt(pa)
        sqrt_pb = math.sqrt(pb)
        sqrt_pc = math.sqrt(pc)

        # 2. Calcular L (Liquidez) e os custos de cada ativo
        amount_btc = 0
        amount_usdt = 0
        L = 0

        if pc <= pa:
            # Preço abaixo do range -> Posição é 100% BTC (Ativo X)
            # V = amount_btc * pc
            # L = (amount_btc * sqrt_pa * sqrt_pb) / (sqrt_pb - sqrt_pa)
            # Resolvendo L em termos de V (capital_usd):
            # L = ( (V / pc) * sqrt_pa * sqrt_pb ) / (sqrt_pb - sqrt_pa)
            if (sqrt_pb - sqrt_pa) == 0: return # Evita Div/0
            L = ( (capital_usd / pc) * sqrt_pa * sqrt_pb ) / (sqrt_pb - sqrt_pa)
            amount_btc = capital_usd / pc
            amount_usdt = 0

        elif pc >= pb:
            # Preço acima do range -> Posição é 100% USDT (Ativo Y)
            # V = amount_usdt
            # L = amount_usdt / (sqrt_pb - sqrt_pa)
            if (sqrt_pb - sqrt_pa) == 0: return # Evita Div/0
            L = capital_usd / (sqrt_pb - sqrt_pa)
            amount_btc = 0
            amount_usdt = capital_usd
        
        else:
            # Preço dentro do range -> Posição tem ambos os ativos
            # V = amount_usdt + amount_btc * pc
            # Onde:
            # amount_usdt = L * (sqrt_pc - sqrt_pa)
            # amount_btc = L * ( (1/sqrt_pc) - (1/sqrt_pb) )
            # Resolvendo L em termos de V (capital_usd):
            # V = L * [ (sqrt_pc - sqrt_pa) + ( (1/sqrt_pc) - (1/sqrt_pb) ) * pc ]
            # V = L * [ sqrt_pc - sqrt_pa + sqrt_pc - (pc / sqrt_pb) ]
            # V = L * [ 2*sqrt_pc - sqrt_pa - (pc / sqrt_pb) ]
            denominator = (2*sqrt_pc - sqrt_pa - (pc / sqrt_pb))
            if denominator == 0: return # Evita Div/0
            
            L = capital_usd / denominator
            amount_usdt = L * (sqrt_pc - sqrt_pa)
            amount_btc = L * ( (1/sqrt_pc) - (1/sqrt_pb) )
            
            # Verificação de sanidade
            calculated_cost = amount_usdt + (amount_btc * pc)
            if not math.isclose(calculated_cost, capital_usd, rel_tol=1e-3):
                # Aviso se o custo calculado diferir muito (pequenas diferenças são normais)
                logger.debug(f"Custo calculado ${calculated_cost:.2f} difere do capital ${capital_usd:.2f}")

        # 3. Deduzir o capital e criar o objeto LP
        self.usd_balance -= capital_usd # Deduz o valor total alocado
        
        new_lp = {
            "id": len(self.active_lps) + 1,
            "L": L, # A métrica de liquidez constante
            "range_lower": range_lower,
            "range_upper": range_upper,
            "open_timestamp": timestamp,
            "entry_price": current_btc_price,
            "initial_capital_usd": capital_usd, # Valor total investido
            "fees_accrued_usdt": 0.0, # Rastrear taxas por token
            "fees_accrued_btc": 0.0,
            # Armazena os montantes iniciais para referência futura
            "initial_amount_btc": amount_btc, 
            "initial_amount_usdt": amount_usdt,
            "days_out_of_range": 0, # Rastrear dias fora do range
        }
        self.active_lps.append(new_lp)
        self.decision_history.append(
            f"[{timestamp.date()}] OPEN LP: ${capital_usd:.2f} @ ${current_btc_price:.2f} | "
            f"Range: ${range_lower:.2f}-${range_upper:.2f} | "
            f"Assets: {amount_btc:.6f} BTC + {amount_usdt:.2f} USDT"
        )

    def close_lp(self, lp_id: int, current_btc_price: float):
        """Fecha uma posição de LP e retorna o valor para o balanço de USD."""
        lp_to_close = next((lp for lp in self.active_lps if lp['id'] == lp_id), None)
        if not lp_to_close:
            logger.warning(f"Tentativa de fechar LP ID {lp_id} inexistente.")
            return

        # TODO: Cálculo de valor real (com IL e taxas) - PRÓXIMO CARTÃO
        # Por agora, aproximação simples
        hodl_value = lp_to_close['initial_capital_usd'] * (current_btc_price / lp_to_close['entry_price'])
        final_value = hodl_value + lp_to_close['fees_accrued_usdt'] # Simplificado

        self.usd_balance += final_value
        self.active_lps.remove(lp_to_close)
        self.decision_history.append(f"CLOSE LP {lp_id}: Valor retornado ${final_value:.2f} @ ${current_btc_price}")

    # --- O Ponto de Entrada Principal ---    
    def close_lp(self, lp_id: int, current_btc_price: float, timestamp):
        """Fecha uma posição de LP e retorna o valor para o balanço de USD."""
        lp_to_close = next((lp for lp in self.active_lps if lp['id'] == lp_id), None)
        if not lp_to_close:
            logger.warning(f"Tentativa de fechar LP ID {lp_id} inexistente.")
            return

        # 1. Calcula o valor dos ATIVOS (com IL)
        asset_value, _, _ = self._get_lp_value(lp_to_close, current_btc_price)
        
        # 2. Calcula o valor das TAXAS acumuladas
        fees_value = lp_to_close['fees_accrued_usdt'] + (lp_to_close['fees_accrued_btc'] * current_btc_price)

        # 3. Valor final é a soma de ativos + taxas
        final_value = asset_value + fees_value

        self.usd_balance += final_value
        self.active_lps.remove(lp_to_close)
        self.decision_history.append(
            f"[{timestamp.date()}] CLOSE LP {lp_id}: Valor retornado ${final_value:.2f} @ ${current_btc_price:.2f} "
            f"(Ativos: ${asset_value:.2f}, Taxas: ${fees_value:.2f})"
        )
 
    def run(self, df: pd.DataFrame, strategy_function):
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
            timestamp = row['Open_time']
            
            # --- 1. Atualizar o estado das LPs ANTES da estratégia ---
            for lp in self.active_lps:
                is_in_range = lp['range_lower'] < current_price < lp['range_upper']

                # 1. Acumular Taxas
                if is_in_range:
                    total_pool_volume_24h = row.get('VolumeUSD', 0)
                    total_pool_tvl_usd = row.get('TVL_USD', 1) 
                    
                    if total_pool_tvl_usd > 0 and total_pool_volume_24h > 0:
                        my_lp_value_usd, _, _ = self._get_lp_value(lp, current_price)
                        my_share_of_pool = my_lp_value_usd / total_pool_tvl_usd
                        total_fees_generated_usd = total_pool_volume_24h * POOL_FEE_RATE
                        fees_earned_today_usd = total_fees_generated_usd * my_share_of_pool
                        lp['fees_accrued_usdt'] += fees_earned_today_usd
                
                # 2. Atualizar Contador "Fora do Range"
                if not is_in_range:
                    lp['days_out_of_range'] += 1
                else:
                    lp['days_out_of_range'] = 0 # Resetar o contador

            # --- 2. Chamar a Estratégia ---
            # (Esta linha estava com a indentação errada)
            # Ela deve estar alinhada com o 'for lp in...' acima, não dentro dele.
            strategy_function(row, self, timestamp)

            # --- 3. Registrar o Valor do Portfólio ---
            total_value = self._calculate_portfolio_value(current_price)
            self.portfolio_history.append(total_value)

        # --- Fim do Backtest ---
        final_portfolio_value = self.portfolio_history[-1] if self.portfolio_history else self.initial_capital
        
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

