import pandas as pd
import numpy as np
import math
import logging
from datetime import timedelta

from defi_data_toolkit.database import log_open_position, log_close_position
from .config import DB_FILE, SIMULATED_GAS_FEE_USD, GAS_RESERVE_USD

logger = logging.getLogger(__name__)

POOL_FEE_RATE = 0.003 
LOAN_TO_VALUE_RATIO = 0.50 
DEBT_INTEREST_RATE = 0.075 
LIQUIDATION_THRESHOLD = 0.80 
LIQUIDATION_PENALTY = 0.10 
# Health Factor risk management thresholds
HF_WARNING_THRESHOLD = 1.3
HF_CRITICAL_THRESHOLD = 1.1
# Refinancing threshold: only refinance (borrow to fund) when HF is sufficiently high
HF_REFINANCE_THRESHOLD = 2.0

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
        # Track reserve alert states to avoid repeated logs (only log on state change)
        self._reserve_warning_active = False
        self._reserve_critical_active = False
        # Emergency cooldown: timestamp until which emergency-close attempts are suppressed
        self._emergency_cooldown_until = None
        
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
        # Charge gas for on-chain buy operation
        if self.usd_balance < SIMULATED_GAS_FEE_USD:
            logger.error("Insufficient USD to pay gas for buy_and_hodl. Aborting operation.")
            return
        self.usd_balance -= SIMULATED_GAS_FEE_USD

        if self.usd_balance < amount_usd:
            logger.warning("Capital insuficiente para comprar HODL.")
            return
            
        btc_bought = amount_usd / current_btc_price
        self.usd_balance -= amount_usd
        self.btc_hodl_balance += btc_bought
        self.decision_history.append(f"HODL BUY: {btc_bought:.6f} BTC @ ${current_btc_price}")

    def add_collateral(self, btc_amount: float):
        """Adiciona BTC ao balanço de colateral HODL."""
        # Charge gas for on-chain add_collateral operation
        if self.usd_balance < SIMULATED_GAS_FEE_USD:
            logger.error("Insufficient USD to pay gas for add_collateral. Aborting operation.")
            return
        self.usd_balance -= SIMULATED_GAS_FEE_USD
        self.btc_hodl_balance += btc_amount

    def open_lp(self, capital_usd: float, range_lower: float, range_upper: float, current_btc_price: float, timestamp, strategy: str = "UNKNOWN"):
        """Abre uma nova posição de LP com matemática da Uniswap v3."""
        # Charge gas for opening an LP
        if self.usd_balance < SIMULATED_GAS_FEE_USD:
            logger.error(f"[{timestamp.date()}] Insufficient USD to pay gas for opening LP. Aborting.")
            return
        self.usd_balance -= SIMULATED_GAS_FEE_USD

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

        new_lp = {
            "L": L, "range_lower": range_lower,
            "range_upper": range_upper, "open_timestamp": timestamp,
            "entry_price": current_btc_price, "initial_capital_usd": capital_usd,
            "fees_accrued_usdt": 0.0, "fees_accrued_btc": 0.0,
            "initial_amount_btc": amount_btc, "initial_amount_usdt": amount_usdt,
            "days_out_of_range": 0 
        }

        position_id = log_open_position(
            db_file=DB_FILE,
            open_timestamp=int(timestamp.value / 10**6), # Converter para ms
            strategy=strategy,
            capital_usd=capital_usd,
            open_price=current_btc_price,
            range_lower=range_lower,
            range_upper=range_upper
        )
        
        if position_id is None:
            logger.error("Falha ao registrar 'open_position' no DB. Abortando abertura de LP.")
            return

        # Adiciona o ID do DB à nossa LP em memória
        new_lp["id"] = position_id
        
        self.active_lps.append(new_lp)
        self.decision_history.append(
            f"[{timestamp.date()}] OPEN LP (ID: {position_id}): ${capital_usd:.2f} @ ${current_btc_price:.2f} | "
            f"Range: ${range_lower:.2f}-${range_upper:.2f} | Strategy: {strategy}"
        )

    def close_lp(self, lp_id: int, current_btc_price: float, timestamp, is_emergency: bool = False) -> bool:
        lp_to_close = next((lp for lp in self.active_lps if lp['id'] == lp_id), None)
        if not lp_to_close:
            logger.warning(f"Tentativa de fechar LP ID {lp_id} inexistente.")
            return False

        # Respect emergency cooldown: if we've recently hit a hard no-gas condition,
        # avoid spamming logs by returning silently during the cooldown window.
        now = pd.Timestamp.now()
        if self._emergency_cooldown_until and now < self._emergency_cooldown_until:
            return False

        # Physical gas requirement: must have at least the gas fee available
        if self.usd_balance < SIMULATED_GAS_FEE_USD:
            # First time we hit this state, escalate to CRITICAL and set a long cooldown
            logger.critical(
                f"[{timestamp.date()}] Insufficient USD to pay gas for closing LP {lp_id}. Aborting and entering long cooldown."
            )
            # Suppress repeated critical spam for a long window (e.g., 2 years)
            self._emergency_cooldown_until = now + timedelta(days=365*2)
            return False

        # If emergency, allow spending below GAS_RESERVE_USD to execute the close
        # (we still enforce the physical gas fee above). For non-emergency closes
        # normal reserve semantics are enforced elsewhere in the engine.
        self.usd_balance -= SIMULATED_GAS_FEE_USD

        asset_value, _, _ = self._get_lp_value(lp_to_close, current_btc_price)
        fees_value = lp_to_close['fees_accrued_usdt'] + (lp_to_close['fees_accrued_btc'] * current_btc_price)
        final_value = asset_value + fees_value

        final_profit = final_value - lp_to_close['initial_capital_usd']
        
        log_close_position(
            db_file=DB_FILE,
            position_id=lp_id,
            close_timestamp=int(timestamp.value / 10**6), # Converter para ms
            close_price=current_btc_price,
            final_profit=final_profit
        )

        self.usd_balance += final_value
        self.active_lps.remove(lp_to_close)
        self.decision_history.append(
            f"[{timestamp.date()}] CLOSE LP {lp_id}: Valor retornado ${final_value:.2f} @ ${current_btc_price:.2f} "
            f"(Lucro/Prejuízo da LP: ${final_profit:.2f})"
        )
        return True

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

    def _check_and_rebalance_health(self, current_price: float):
        """Checks health factor and attempts to defend the position by using
        available cash to buy collateral or closing LPs in emergency.

        This method is conservative: it first tries to use USD cash (while respecting
        the GAS_RESERVE) to buy BTC collateral; if that is insufficient and the HF 
        is critical, it will close the most recent LP to free liquidity and pay down debt.
        """
        # Nothing to do if no debt
        if self.total_debt_usd <= 0:
            return

        collateral_value = self.btc_hodl_balance * current_price
        hf = (collateral_value * LIQUIDATION_THRESHOLD) / self.total_debt_usd if self.total_debt_usd > 0 else 999.0

        # Safe zone
        if hf > HF_WARNING_THRESHOLD:
            return

        # Gas Solvency Check: trigger earlier to avoid deadlock. If the USD balance
        # has fallen below half the declared gas reserve, attempt an emergency close
        # of the single most-profitable LP. This is designed to run before the
        # balance reaches the physical gas-fee limit.
        if self.usd_balance < (GAS_RESERVE_USD * 0.5) and self.active_lps:
            now = pd.Timestamp.now()
            # Respect an emergency cooldown if we've already failed recently
            if self._emergency_cooldown_until and now < self._emergency_cooldown_until:
                return

            # Must have at least one gas payment available to execute a close
            if self.usd_balance < SIMULATED_GAS_FEE_USD:
                logger.critical(
                    f"USD balance ${self.usd_balance:.2f} < required gas ${SIMULATED_GAS_FEE_USD:.2f}; cannot perform emergency close. Entering long cooldown."
                )
                # Suppress repeated critical spam for a long window (e.g., 2 years)
                self._emergency_cooldown_until = now + timedelta(days=365*2)
                return

            # Evaluate liquidation / current value for each LP and pick the most valuable
            best_lp = None
            best_value = -1.0
            for lp in self.active_lps:
                asset_value, _, _ = self._get_lp_value(lp, current_price)
                fees_value = lp['fees_accrued_usdt'] + (lp['fees_accrued_btc'] * current_price)
                total_value = asset_value + fees_value
                if total_value > best_value:
                    best_value = total_value
                    best_lp = lp

            if best_lp is not None:
                ts = pd.Timestamp.now()
                logger.warning(
                    f"EMERGENCY SOLVENCY: USD ${self.usd_balance:.2f} < {GAS_RESERVE_USD*0.5:.2f}. "
                    f"Attempting emergency close of most-profitable LP ID {best_lp['id']} (value=${best_value:.2f})."
                )
                closed = self.close_lp(lp_id=best_lp['id'], current_btc_price=current_price, timestamp=ts, is_emergency=True)
                if not closed:
                    logger.critical(
                        "Emergency close failed (insufficient funds to even pay gas). Entering long cooldown to avoid spam."
                    )
                    self._emergency_cooldown_until = now + timedelta(days=365*2)
                # After attempting an emergency close return — let subsequent health checks run on next tick
                return

        # Danger zone: try to rebalance using available cash (respecting gas reserve)
        available_for_rescue = self.usd_balance - GAS_RESERVE_USD
        if available_for_rescue > 10:
            amount_to_use = available_for_rescue
            # Buy and add to collateral
            self.buy_and_hodl(amount_to_use, current_price)
            # usd_balance reduced by buy_and_hodl
            # buy_and_hodl already subtracts from usd_balance and increases btc_hodl_balance
            logger.info("REBALANCE: Usando Caixa para comprar Colateral e defender HF (Respeitando reserva de gás)")

            # Recompute HF
            collateral_value = self.btc_hodl_balance * current_price
            hf = (collateral_value * LIQUIDATION_THRESHOLD) / self.total_debt_usd if self.total_debt_usd > 0 else 999.0

            # If rebalance succeeded, return
            if hf > HF_WARNING_THRESHOLD:
                return

        # Critical zone: close most recent LP to free liquidity and pay debt
        if hf < HF_CRITICAL_THRESHOLD and self.active_lps:
            # Close the most recently opened LP (last in list)
            lp = self.active_lps[-1]
            # Close LP and receive funds into usd_balance
            ts = pd.Timestamp.now()
            self.close_lp(lp_id=lp['id'], current_btc_price=current_price, timestamp=ts)

            # Immediately use available USD to pay down debt (as much as possible)
            # But ensure we keep the gas reserve intact
            available_for_debt_payment = max(0, self.usd_balance - GAS_RESERVE_USD)
            pay_amount = min(available_for_debt_payment, self.total_debt_usd)
            if pay_amount > 0:
                self.total_debt_usd -= pay_amount
                self.usd_balance -= pay_amount
                logger.info("EMERGENCY: Fechando LP e pagando dívida para evitar liquidação! (Reserva de gás protegida)")
            return


    def _check_and_harvest(self, current_price: float, timestamp):
        """Smart Harvest: Collects accrued fees with reserve-aware routing.
        
        Rules:
        1. Early exit if USD balance is too low to pay gas
        2. Check if gas reserve needs refilling (usd_balance < GAS_RESERVE_USD)
        3. If reserve is low (needs_refill=True):
           - Convert ALL fees to USD (BTC fees -> simulate swap to USD)
           - Use lower threshold (GAS * 2 instead of GAS * 10)
           - Log "HARVEST (REFILL MODE)"
        4. If reserve is healthy (needs_refill=False):
           - Keep existing auto-compound logic (BTC -> Collateral, USD -> Balance)
           - Use standard threshold (GAS * 10)
           - Log "HARVEST (AUTO-COMPOUND MODE)"
        5. Deduct SIMULATED_GAS_FEE_USD from usd_balance
        """
        if not self.active_lps:
            return

        # Early exit if we don't have enough USD for gas
        if self.usd_balance < SIMULATED_GAS_FEE_USD:
            return

        # Check if gas reserve needs refilling
        needs_refill = self.usd_balance < GAS_RESERVE_USD

        for lp in self.active_lps:
            # Calculate total fees in USD
            fees_btc_in_usd = lp['fees_accrued_btc'] * current_price
            total_fees_usd = lp['fees_accrued_usdt'] + fees_btc_in_usd
            
            # Determine harvest threshold based on reserve health
            if needs_refill:
                # Emergency mode: Accept lower margins to refill reserve
                harvest_threshold = SIMULATED_GAS_FEE_USD * 2
            else:
                # Normal mode: Only harvest if fees justify the cost
                harvest_threshold = SIMULATED_GAS_FEE_USD * 10
            
            if total_fees_usd <= harvest_threshold:
                continue
            
            # Deduct gas fee from USD balance
            if self.usd_balance < SIMULATED_GAS_FEE_USD:
                continue
            
            self.usd_balance -= SIMULATED_GAS_FEE_USD
            
            # Route fees based on reserve health
            if needs_refill:
                # REFILL MODE: Convert ALL fees to USD to replenish the gas reserve
                # Simulate BTC-to-USD swap by adding equivalent USD value
                btc_fees_in_usd = lp['fees_accrued_btc'] * current_price
                self.usd_balance += btc_fees_in_usd
                
                # Route USD fees directly to balance
                if lp['fees_accrued_usdt'] > 0:
                    self.usd_balance += lp['fees_accrued_usdt']
                
                # Log the refill harvest
                self.decision_history.append(
                    f"[{timestamp.date()}] HARVEST (REFILL MODE) LP {lp['id']}: "
                    f"+{lp['fees_accrued_btc']:.6f} BTC (${btc_fees_in_usd:.2f}) converted to USD, "
                    f"+${lp['fees_accrued_usdt']:.2f} to USD, "
                    f"-${SIMULATED_GAS_FEE_USD:.2f} Gas. "
                    f"Reserve refill in progress (Current: ${self.usd_balance:.2f})"
                )
            else:
                # HEALTHY MODE: Auto-compound strategy (existing logic)
                # Route BTC fees to collateral
                if lp['fees_accrued_btc'] > 0:
                    self.add_collateral(lp['fees_accrued_btc'])
                
                # Route USD fees to cash balance
                if lp['fees_accrued_usdt'] > 0:
                    self.usd_balance += lp['fees_accrued_usdt']
                
                # Log the auto-compound harvest
                self.decision_history.append(
                    f"[{timestamp.date()}] HARVEST (AUTO-COMPOUND) LP {lp['id']}: "
                    f"+{lp['fees_accrued_btc']:.6f} BTC to Collateral, "
                    f"+${lp['fees_accrued_usdt']:.2f} to USD, "
                    f"-${SIMULATED_GAS_FEE_USD:.2f} Gas"
                )
            
            # Reset accrued fees after harvest
            lp['fees_accrued_btc'] = 0.0
            lp['fees_accrued_usdt'] = 0.0


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
            # 2. Acumular Juros (se houver dívida) — agora os juros são capitalizados
            #     em `self.total_debt_usd` (comportamento de DeFi: juros acruados na dívida),
            #     e NÃO são deduzidos do saldo USD. Isso preserva liquidez para gas
            #     e oportunidades de mercado.
            if self.total_debt_usd > 0:
                daily_interest_rate = (self.loan_apy / 365)
                interest_cost = self.total_debt_usd * daily_interest_rate

                # Capitalize interest into the outstanding debt (compound interest)
                self.total_debt_usd += interest_cost
            
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

            # 4. Smart Harvest: Collect fees if profitable
            try:
                self._check_and_harvest(current_price, timestamp)
            except Exception as e:
                logger.exception("Erro durante smart harvest: %s", e)

            # 5. Chamar a Estratégia
            # (A estratégia agora verá o self.usd_balance já com os juros descontados)
            # Before taking new strategic decisions, ensure HF is acceptable
            try:
                self._check_and_rebalance_health(current_price)
            except Exception as e:
                logger.exception("Erro durante check/rebalance de HF: %s", e)

            strategy_function(row, self, timestamp)
            
            # 6. Registrar o Valor do Portfólio
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

