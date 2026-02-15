import os
import pandas as pd
import numpy as np
import math
import logging
from datetime import timedelta
from decimal import Decimal

from backend.src.data.storage import log_open_position, log_close_position
from ..config import SIMULATED_GAS_FEE_USD, GAS_RESERVE_USD, SLIPPAGE_PCT
from ..utils.math import calculate_lp_value, calculate_liquidity_l
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)

POOL_FEE_RATE = 0.003 
LOAN_TO_VALUE_RATIO = 0.50 
DEBT_INTEREST_RATE = 0.075

class TradingEngine:
    
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
        self.transaction_log = []  # V13: Structured transaction logging
        # Track reserve alert states to avoid repeated logs (only log on state change)
        self._reserve_warning_active = False
        self._reserve_critical_active = False
        # Emergency cooldown: timestamp until which emergency-close attempts are suppressed
        self._emergency_cooldown_until = None

        self._audit_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "audit.csv")
        )
        with open(self._audit_path, "w", encoding="utf-8") as audit_file:
            audit_file.write("Timestamp,Action,BTC_Price,USD_Balance,Total_Debt,BTC_Hodl,Net_Worth,Health_Factor\n")
        
        # Initialize Risk Manager
        self.risk_manager = RiskManager(
            gas_reserve_usd=GAS_RESERVE_USD,
            simulated_gas_fee_usd=SIMULATED_GAS_FEE_USD
        )
        
        logger.info(f"TradingEngine v2 (Market Timing Loop) inicializado com ${initial_capital_usd} USD.")

    def _log_transaction(self, timestamp: pd.Timestamp, action_type: str, btc_price: float, 
                        usd_amount: float = 0.0, btc_amount: float = 0.0, fee_usd: float = 0.0, 
                        pnl_usd: float = 0.0, details: str = ""):
        """
        V13: Log structured transactions for frontend visualization.
        
        Args:
            timestamp: Transaction timestamp
            action_type: Type of transaction (BUY_HODL, OPEN_LP, CLOSE_LP, HARVEST, DEBT_REPAY, EMERGENCY_CLOSE, etc.)
            btc_price: Current BTC price in USD
            usd_amount: Amount in USD involved
            btc_amount: Amount in BTC involved
            fee_usd: Gas fee or other fees
            pnl_usd: Profit/Loss for this transaction (mainly for CLOSE_LP)
            details: Additional context
        """
        transaction = {
            "timestamp": timestamp,
            "action": action_type,
            "btc_price": btc_price,
            "usd_amount": usd_amount,
            "btc_amount": btc_amount,
            "fee_usd": fee_usd,
            "pnl_usd": pnl_usd,
            "details": details
        }
        self.transaction_log.append(transaction)

        collateral_value = self.btc_hodl_balance * btc_price
        net_worth = self._calculate_portfolio_value(btc_price)
        if self.total_debt_usd > 0:
            health_factor = self.risk_manager.calculate_health_factor(collateral_value, self.total_debt_usd)
        else:
            health_factor = 999.0

        ts_value = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)
        with open(self._audit_path, "a", encoding="utf-8") as audit_file:
            audit_file.write(
                f"{ts_value},{action_type},{btc_price:.8f},{self.usd_balance:.8f},{self.total_debt_usd:.8f},"
                f"{self.btc_hodl_balance:.8f},{net_worth:.8f},{health_factor:.8f}\n"
            )

    def borrow_funds(self, amount: float, current_btc_price: float) -> float:
        if amount <= 0:
            return 0.0
        if self.usd_balance < 0:
            return 0.0

        net_worth = self._calculate_portfolio_value(current_btc_price)
        if net_worth < (self.total_debt_usd * 0.10):
            return 0.0

        self.total_debt_usd += amount
        self.usd_balance += amount

        self._log_transaction(
            timestamp=pd.Timestamp.now(),
            action_type="BORROW",
            btc_price=current_btc_price,
            usd_amount=amount,
            btc_amount=0.0,
            fee_usd=0.0,
            details=""
        )
        return amount

    def _get_lp_value(self, lp: dict, current_btc_price: float) -> tuple:
        """Calculate LP position value using Uniswap V3 math.
        
        Converts all inputs to Decimal for precision.
        Returns tuple of (Decimal, Decimal, Decimal).
        """
        return calculate_lp_value(
            liquidity=lp['L'],
            range_lower=lp['range_lower'],
            range_upper=lp['range_upper'],
            current_price=Decimal(str(current_btc_price))
        )

    def _calculate_portfolio_value(self, current_btc_price: float) -> float:
        if self.is_liquidated:
            return 0.0

        lp_total_value = 0.0
        for lp in self.active_lps:
            asset_value, _, _ = self._get_lp_value(lp, current_btc_price)
            # Convert Decimal result to float for portfolio calculations
            asset_value = float(asset_value)
            fees_value = lp['fees_accrued_usdt'] + (lp['fees_accrued_btc'] * current_btc_price)
            lp_total_value += asset_value + fees_value
            
        hodl_value = self.btc_hodl_balance * current_btc_price
        cash_value = self.usd_balance
        debt_value = self.total_debt_usd
        
        net_value = (hodl_value + lp_total_value + cash_value) - debt_value
        return net_value

    def buy_and_hodl(self, amount_usd: float, current_btc_price: float, timestamp: pd.Timestamp = None):
        """Aloca capital de USD para a carteira HODL de BTC."""
        if timestamp is None:
            timestamp = pd.Timestamp.now()
            
        # 1. BLINDAGEM: Nunca gastar mais do que tem
        # Se o saldo for menor que a taxa, aborta.
        if self.usd_balance < SIMULATED_GAS_FEE_USD:
            # logger.warning("Saldo insuficiente para cobrir Gas. Operação cancelada.")
            return

        # 2. BLINDAGEM: Ajusta o valor da compra ao saldo real disponível
        # Se a estratégia pediu $1 milhão, mas só tem $10, gasta só $10 (menos a taxa)
        actual_available = self.usd_balance - SIMULATED_GAS_FEE_USD
        if amount_usd > actual_available:
            # Opcional: Logar que houve corte no pedido
            amount_usd = actual_available

        if amount_usd <= 0:
            return

        # Cobra a taxa
        self.usd_balance -= SIMULATED_GAS_FEE_USD

        # Executa a compra
        effective_price = current_btc_price * (1 + SLIPPAGE_PCT)
        btc_bought = amount_usd / effective_price
        
        # Deduz do saldo (que agora garantimos ser positivo)
        self.usd_balance -= amount_usd
        self.btc_hodl_balance += btc_bought
        
        # Log...
        self._log_transaction(
            timestamp=timestamp,
            action_type="BUY_HODL",
            btc_price=effective_price,
            usd_amount=amount_usd,
            btc_amount=btc_bought,
            fee_usd=SIMULATED_GAS_FEE_USD,
            details=""
        )
        
        self.decision_history.append(f"HODL BUY: {btc_bought:.6f} BTC @ ${effective_price}")

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

        # Calculate liquidity L and initial amounts using Uniswap V3 math
        # Convert all inputs to Decimal for precision
        effective_price = current_btc_price * (1 + SLIPPAGE_PCT)
        L, amount_btc, amount_usdt = calculate_liquidity_l(
            capital_usd=Decimal(str(capital_usd)),
            range_lower=Decimal(str(range_lower)),
            range_upper=Decimal(str(range_upper)),
            current_price=Decimal(str(effective_price))
        )
        
        # Check for invalid liquidity calculation
        if L == Decimal('0'):
            return

        new_lp = {
            "L": float(L), "range_lower": float(range_lower),
            "range_upper": float(range_upper), "open_timestamp": timestamp,
            "entry_price": effective_price, "initial_capital_usd": capital_usd,
            "fees_accrued_usdt": 0.0, "fees_accrued_btc": 0.0,
            "initial_amount_btc": float(amount_btc), "initial_amount_usdt": float(amount_usdt),
            "days_out_of_range": 0 
        }

        position_id = log_open_position(
            open_timestamp=int(timestamp.value / 10**6), # Converter para ms
            strategy=strategy,
            capital_usd=capital_usd,
            open_price=effective_price,
            range_lower=range_lower,
            range_upper=range_upper
        )
        
        if position_id is None:
            logger.error("Falha ao registrar 'open_position' no DB. Abortando abertura de LP.")
            return

        # Adiciona o ID do DB à nossa LP em memória
        new_lp["id"] = position_id
        
        self.active_lps.append(new_lp)
        
        # V13: Log transaction
        self._log_transaction(
            timestamp=timestamp,
            action_type="OPEN_LP",
            btc_price=effective_price,
            usd_amount=capital_usd,
            btc_amount=float(amount_btc),
            fee_usd=SIMULATED_GAS_FEE_USD,
            details=f"Range: ${range_lower:.2f}-${range_upper:.2f} | Strategy: {strategy} | LP_ID: {position_id}"
        )
        
        self.decision_history.append(
            f"[{timestamp.date()}] OPEN LP (ID: {position_id}): ${capital_usd:.2f} @ ${effective_price:.2f} | "
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

        effective_price = current_btc_price * (1 - SLIPPAGE_PCT)
        asset_value, _, _ = self._get_lp_value(lp_to_close, effective_price)
        # Convert Decimal results to float for compatibility
        asset_value = float(asset_value)
        fees_value = lp_to_close['fees_accrued_usdt'] + (lp_to_close['fees_accrued_btc'] * effective_price)
        final_value = asset_value + fees_value

        final_profit = final_value - lp_to_close['initial_capital_usd']
        
        log_close_position(
            position_id=lp_id,
            close_timestamp=int(timestamp.value / 10**6), # Converter para ms
            close_price=effective_price,
            final_profit=final_profit
        )

        self.usd_balance += final_value
        self.active_lps.remove(lp_to_close)
        
        # V13: Log transaction with PnL
        self._log_transaction(
            timestamp=timestamp,
            action_type="CLOSE_LP",
            btc_price=effective_price,
            usd_amount=final_value,
            btc_amount=0.0,
            fee_usd=SIMULATED_GAS_FEE_USD,
            pnl_usd=final_profit,
            details=f"LP_ID: {lp_id} | Initial: ${lp_to_close['initial_capital_usd']:.2f}"
        )
        
        self.decision_history.append(
            f"[{timestamp.date()}] CLOSE LP {lp_id}: Valor retornado ${final_value:.2f} @ ${effective_price:.2f} "
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
        """Checks health factor and attempts to defend the position using RiskManager.

        Delegates risk assessment to RiskManager and acts on recommendations:
        1. Emergency close if gas solvency is at risk
        2. Use available cash to buy collateral
        3. Close LPs if health is critical
        """
        # Nothing to do if no debt
        if self.total_debt_usd <= 0:
            return

        collateral_value = self.btc_hodl_balance * current_price
        health_status, hf = self.risk_manager.check_health_status(collateral_value, self.total_debt_usd)

        # Safe zone - no action needed
        if health_status == 'SAFE':
            return

        # Get rebalancing recommendations from RiskManager
        rebalance_options = self.risk_manager.assess_rebalance_options(
            health_factor=hf,
            balance=self.usd_balance,
            has_active_lps=len(self.active_lps) > 0
        )

        action = rebalance_options['action']

        # EMERGENCY CLOSE: Gas solvency issue
        if action == 'emergency_close':
            now = pd.Timestamp.now()
            # Respect an emergency cooldown if we've already failed recently
            if self._emergency_cooldown_until and now < self._emergency_cooldown_until:
                return

            # Must have at least one gas payment available to execute a close
            if not self.risk_manager.can_afford_gas(self.usd_balance):
                logger.critical(
                    f"USD balance ${self.usd_balance:.2f} < required gas ${SIMULATED_GAS_FEE_USD:.2f}; cannot perform emergency close. Entering long cooldown."
                )
                # Suppress repeated critical spam for a long window (e.g., 2 years)
                self._emergency_cooldown_until = now + timedelta(days=365*2)
                return

            # Find the most valuable LP to close
            best_lp = None
            best_value = -1.0
            for lp in self.active_lps:
                asset_value, _, _ = self._get_lp_value(lp, current_price)
                # Convert Decimal result to float for comparison
                asset_value = float(asset_value)
                fees_value = lp['fees_accrued_usdt'] + (lp['fees_accrued_btc'] * current_price)
                total_value = asset_value + fees_value
                if total_value > best_value:
                    best_value = total_value
                    best_lp = lp

            if best_lp is not None:
                ts = pd.Timestamp.now()
                logger.warning(
                    f"EMERGENCY SOLVENCY: {rebalance_options['reason']}. "
                    f"Attempting emergency close of most-profitable LP ID {best_lp['id']} (value=${best_value:.2f})."
                )
                closed = self.close_lp(lp_id=best_lp['id'], current_btc_price=current_price, timestamp=ts, is_emergency=True)
                if not closed:
                    logger.critical(
                        "Emergency close failed (insufficient funds to even pay gas). Entering long cooldown to avoid spam."
                    )
                    self._emergency_cooldown_until = now + timedelta(days=365*2)
            return

        # USE CASH: Try to rebalance using available cash
        elif action == 'use_cash':
            available_cash = rebalance_options['available_cash']
            if available_cash > 10:
                # Buy and add to collateral
                ts = pd.Timestamp.now()
                btc_bought = available_cash / current_price
                self.buy_and_hodl(available_cash, current_price, timestamp=ts)
                
                # V13: Log debt repayment action (rebalance with cash)
                self._log_transaction(
                    timestamp=ts,
                    action_type="DEBT_REPAY",
                    btc_price=current_price,
                    usd_amount=available_cash,
                    btc_amount=btc_bought,
                    fee_usd=SIMULATED_GAS_FEE_USD,
                    details="Emergency collateral boost to improve HF"
                )
                
                logger.info(
                    f"REBALANCE: {rebalance_options['reason']}. "
                    f"Using ${available_cash:.2f} to buy collateral (Gas reserve protected)"
                )

                # Recompute HF to check if rebalance succeeded
                collateral_value = self.btc_hodl_balance * current_price
                new_status, new_hf = self.risk_manager.check_health_status(collateral_value, self.total_debt_usd)
                
                if new_status == 'SAFE':
                    return

        # CLOSE LP: Critical health factor, need to close LP and pay debt
        if action == 'close_lp' and self.active_lps:
            # Close the most recently opened LP (last in list)
            lp = self.active_lps[-1]
            ts = pd.Timestamp.now()
            self.close_lp(lp_id=lp['id'], current_btc_price=current_price, timestamp=ts)

            # Use available USD to pay down debt (respecting gas reserve)
            safe_balance = self.risk_manager.calculate_safe_balance(self.usd_balance)
            pay_amount = min(safe_balance, self.total_debt_usd)
            if pay_amount > 0:
                self.total_debt_usd -= pay_amount
                self.usd_balance -= pay_amount
                logger.info(
                    f"EMERGENCY: {rebalance_options['reason']}. "
                    f"Closed LP and paid ${pay_amount:.2f} debt (Gas reserve protected)"
                )
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
                
                # V13: Log harvest
                total_fees_usd_value = btc_fees_in_usd + lp['fees_accrued_usdt']
                self._log_transaction(
                    timestamp=timestamp,
                    action_type="HARVEST",
                    btc_price=current_price,
                    usd_amount=total_fees_usd_value,
                    btc_amount=lp['fees_accrued_btc'],
                    fee_usd=SIMULATED_GAS_FEE_USD,
                    details=f"LP_ID: {lp['id']} | Mode: REFILL | BTC->USD conversion"
                )
                
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
                
                # V13: Log harvest
                total_fees_usd_value = lp['fees_accrued_btc'] * current_price + lp['fees_accrued_usdt']
                self._log_transaction(
                    timestamp=timestamp,
                    action_type="HARVEST",
                    btc_price=current_price,
                    usd_amount=total_fees_usd_value,
                    btc_amount=lp['fees_accrued_btc'],
                    fee_usd=SIMULATED_GAS_FEE_USD,
                    details=f"LP_ID: {lp['id']} | Mode: AUTO_COMPOUND | BTC->Collateral"
                )
                
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


    def run(self, df: pd.DataFrame, strategy):
        """
        Run the backtest with a given strategy.
        
        Args:
            df: DataFrame with market data
            strategy: Strategy instance implementing BaseStrategy
        """
        if df.empty:
            logger.error("DataFrame vazio. Abortando backtest.")
            return {}

        logger.info(f"Iniciando TradingEngine v2 (Market Timing Loop) com {strategy.get_name()}. Processando {len(df)} velas...")
        
        # Store backtest period dates
        backtest_start_date = df.iloc[0]['Open_time']
        backtest_end_date = df.iloc[-1]['Open_time']
        
        # Store initial and final BTC prices for HODL benchmark calculation
        initial_btc_price = df.iloc[0]['Close']
        final_btc_price = df.iloc[-1]['Close']
        
        for index, row in df.iterrows():
            if self.usd_balance <= 0:
                logger.warning("Bankruptcy Triggered")
                break
            if self.is_liquidated:
                self.portfolio_history.append(0.0)
                continue

            current_price = row['Close']
            timestamp = row['Open_time']
            
            # 1. Calcular HF e checar Liquidação (se houver dívida)
            if self.total_debt_usd > 0:
                collateral_value = self.btc_hodl_balance * current_price
                self.health_factor = self.risk_manager.calculate_health_factor(collateral_value, self.total_debt_usd)
                
                if self.risk_manager.is_liquidated(self.health_factor):
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
                        # Convert Decimal result to float for fee calculations
                        my_lp_value_usd = float(my_lp_value_usd)
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

            strategy.execute(row, self, timestamp)
            
            # 6. Registrar o Valor do Portfólio
            total_net_value = self._calculate_portfolio_value(current_price)
            self.portfolio_history.append(total_net_value)

        # --- Fim do Backtest ---
        final_portfolio_value = self.portfolio_history[-1] if self.portfolio_history else self.initial_capital
        
        # Calculate HODL benchmark using ONLY price change, independent of strategy performance
        hodl_btc_amount = self.initial_capital / initial_btc_price
        hodl_final_value = hodl_btc_amount * final_btc_price
        
        logger.info("TradingEngine v2 Concluído. Valor Final: $%.2f", final_portfolio_value)
        logger.info("HODL Benchmark Final Value: $%.2f (Preço Inicial: $%.2f → Preço Final: $%.2f)", 
                    hodl_final_value, initial_btc_price, final_btc_price)

        return {
            'initial_capital_usd': self.initial_capital,
            'final_usd_value': final_portfolio_value,
            'profit_usd': final_portfolio_value - self.initial_capital,
            'profit_percentage_usd': ((final_portfolio_value / self.initial_capital) - 1) * 100,
            'btc_benchmark_final_value': hodl_final_value,
            'btc_benchmark_profit_percentage': ((hodl_final_value / self.initial_capital) - 1) * 100,
            'backtest_start_date': backtest_start_date.isoformat() if hasattr(backtest_start_date, 'isoformat') else str(backtest_start_date),
            'backtest_end_date': backtest_end_date.isoformat() if hasattr(backtest_end_date, 'isoformat') else str(backtest_end_date),
            'decision_history': self.decision_history,
            'transaction_log': self.transaction_log,  # V13: Include transaction log
        }

