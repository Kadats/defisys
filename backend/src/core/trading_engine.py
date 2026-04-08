import os
import pandas as pd
import numpy as np
import math
import logging
from datetime import timedelta
from decimal import Decimal

from backend.src.data.storage import log_open_position, log_close_position
from ..config import SIMULATED_GAS_FEE_USD, GAS_RESERVE_USD, SLIPPAGE_PCT, DEFAULT_INTERVAL, MAX_GLOBAL_DRAWDOWN, MAX_DAILY_DRAWDOWN
from ..utils.math import calculate_lp_value, calculate_liquidity_l
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)

POOL_FEE_RATE = 0.003 
LOAN_TO_VALUE_RATIO = 0.50 
DEBT_INTEREST_RATE = 0.075

class TradingEngine:
    
    def __init__(self, initial_capital_usd: float = 1000.0, gas_fee_usd: float = SIMULATED_GAS_FEE_USD, slippage_pct: float = SLIPPAGE_PCT):
        self.initial_capital = initial_capital_usd
        self.usd_balance = initial_capital_usd 
        self.btc_hodl_balance = 0.0
        self.btc_collateral_balance = 0.0
        self.total_debt_usd = 0.0             
        self.loan_apy = DEBT_INTEREST_RATE
        from backend.src.strategies.yield_manager import AaveYieldManager
        self.yield_manager = AaveYieldManager()
        self.gas_fee_usd = gas_fee_usd
        self.slippage_pct = slippage_pct
        self.health_factor = 999.0
        self.is_liquidated = False
        self.is_killed = False
        self.global_hwm = initial_capital_usd
        self.daily_hwm_window = []
        self.active_lps = []
        self.active_shorts = []
        self.portfolio_history = []
        self.decision_history = []
        self.transaction_log = []
        self._reserve_warning_active = False
        self._audit_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "audit.csv"))
        with open(self._audit_path, "w", encoding="utf-8") as f: f.write("Timestamp,Action,BTC_Price,USD_Balance,Total_Debt,BTC_Hodl,Net_Worth,Health_Factor\n")
        self.risk_manager = RiskManager(gas_reserve_usd=GAS_RESERVE_USD, simulated_gas_fee_usd=self.gas_fee_usd, max_global_drawdown=MAX_GLOBAL_DRAWDOWN, max_daily_drawdown=MAX_DAILY_DRAWDOWN)
        logger.info(f"TradingEngine v2 inicializado com ${initial_capital_usd} USD.")

    def _log_transaction(self, timestamp, action_type, btc_price, usd_amount=0.0, btc_amount=0.0, fee_usd=0.0, pnl_usd=0.0, details=""):
        net_worth = self._calculate_portfolio_value(btc_price)
        transaction = {"timestamp": timestamp, "action": action_type, "btc_price": btc_price, "usd_amount": usd_amount, "btc_amount": btc_amount, "fee_usd": fee_usd, "pnl_usd": pnl_usd, "post_trade_equity": net_worth, "details": details}
        self.transaction_log.append(transaction)
        ts_v = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)
        with open(self._audit_path, "a", encoding="utf-8") as f: f.write(f"{ts_v},{action_type},{btc_price:.8f},{self.usd_balance:.8f},{self.total_debt_usd:.8f},{self.btc_hodl_balance:.8f},{net_worth:.8f},{self.health_factor:.8f}\n")

    def _get_lp_value(self, lp, current_btc_price):
        return calculate_lp_value(liquidity=lp['L'], range_lower=lp['range_lower'], range_upper=lp['range_upper'], current_price=Decimal(str(current_btc_price)))

    def _calculate_portfolio_value(self, current_btc_price):
        lp_val = sum([float(self._get_lp_value(lp, current_btc_price)[0]) + lp['fees_accrued_usdt'] + (lp['fees_accrued_btc'] * current_btc_price) for lp in self.active_lps])
        short_val = sum([s['collateral_usd'] + (s['entry_price'] - current_btc_price) * s['btc_amount'] for s in self.active_shorts])
        return (self.btc_hodl_balance + self.btc_collateral_balance) * current_btc_price + self.usd_balance + lp_val + short_val + self.yield_manager.get_total_balance() - self.total_debt_usd

    def allocate_to_yield(self, amount, timestamp):
        if amount > 0 and self.usd_balance >= amount and self.yield_manager.deposit_usd(amount):
            self.usd_balance -= amount
            self.decision_history.append(f"[{timestamp.date()}] AAVE DEPOSIT: ${amount:.2f}")

    def withdraw_from_yield(self, amount=None, timestamp=None):
        withdrawn = self.yield_manager.withdraw_usd(amount)
        if withdrawn > 0:
            self.usd_balance += withdrawn
            if timestamp: self.decision_history.append(f"[{timestamp.date()}] AAVE WITHDRAW: ${withdrawn:.2f}")

    def _volume_per_candle(self, volume_24h):
        interval = (DEFAULT_INTERVAL or "4h").strip().lower()
        cpd = max(1, int(24 / int(interval[:-1]))) if 'h' in interval else 1
        return volume_24h / cpd

    def buy_and_hodl(self, amount_usd, current_btc_price, timestamp=None):
        if timestamp is None: timestamp = pd.Timestamp.now()
        if self.usd_balance < amount_usd + self.gas_fee_usd: self.withdraw_from_yield(timestamp=timestamp)
        actual = min(amount_usd, self.usd_balance - self.gas_fee_usd)
        if actual <= 0: return
        self.usd_balance -= (self.gas_fee_usd + actual)
        eff_price = current_btc_price * (1 + self.slippage_pct)
        btc_bought = actual / eff_price
        self.btc_hodl_balance += btc_bought
        self._log_transaction(timestamp, "BUY_HODL", eff_price, actual, btc_bought, self.gas_fee_usd)

    def sell_btc(self, btc_amount, current_btc_price, timestamp=None):
        if timestamp is None: timestamp = pd.Timestamp.now()
        if self.btc_hodl_balance < btc_amount or self.usd_balance < self.gas_fee_usd: return 0.0
        self.usd_balance -= self.gas_fee_usd
        eff_price = current_btc_price * (1 - self.slippage_pct)
        usd_rec = btc_amount * eff_price
        self.btc_hodl_balance -= btc_amount
        self.usd_balance += usd_rec
        self._log_transaction(timestamp, "SELL_BTC", eff_price, usd_rec, btc_amount, self.gas_fee_usd)
        return usd_rec

    def open_lp(self, capital_usd, range_lower, range_upper, current_btc_price, timestamp, strategy="UNKNOWN"):
        if self.usd_balance < capital_usd + self.gas_fee_usd: self.withdraw_from_yield(timestamp=timestamp)
        actual = self.risk_manager.adjust_position_size(capital_usd, self.usd_balance, self.gas_fee_usd, self.risk_manager.gas_reserve_usd)
        if actual <= 0 or range_lower >= range_upper: return None
        eff_price = current_btc_price * (1 + self.slippage_pct)
        L, btc, usdt = calculate_liquidity_l(Decimal(str(actual)), Decimal(str(range_lower)), Decimal(str(range_upper)), Decimal(str(eff_price)))
        if L == Decimal('0'): return None
        pos_id = log_open_position(int(timestamp.value/10**6), strategy, actual, eff_price, range_lower, range_upper)
        if pos_id is None: return None
        self.usd_balance -= (self.gas_fee_usd + actual)
        self.active_lps.append({"id": pos_id, "L": float(L), "range_lower": float(range_lower), "range_upper": float(range_upper), "open_timestamp": timestamp, "entry_price": eff_price, "initial_capital_usd": actual, "fees_accrued_usdt": 0.0, "fees_accrued_btc": 0.0, "initial_amount_btc": float(btc), "initial_amount_usdt": float(usdt), "days_out_of_range": 0})
        self._log_transaction(timestamp, "OPEN_LP", eff_price, actual, float(btc), self.gas_fee_usd, details=f"LP_ID: {pos_id}")
        return pos_id

    def close_lp(self, lp_id, current_btc_price, timestamp, is_emergency=False):
        lp = next((l for l in self.active_lps if l['id'] == lp_id), None)
        if not lp or self.usd_balance < self.gas_fee_usd: return False
        self.usd_balance -= self.gas_fee_usd
        eff_price = current_btc_price * (1 - self.slippage_pct)
        val = float(self._get_lp_value(lp, eff_price)[0]) + lp['fees_accrued_usdt'] + (lp['fees_accrued_btc'] * eff_price)
        profit = val - lp['initial_capital_usd']
        log_close_position(lp_id, int(timestamp.value/10**6), eff_price, profit)
        self.usd_balance += val
        self.active_lps.remove(lp)
        self._log_transaction(timestamp, "CLOSE_LP", eff_price, val, 0, self.gas_fee_usd, profit)
        return True

    def open_short(self, capital_usd, current_btc_price, timestamp, strategy="SHORT"):
        if self.is_killed: return None
        if self.usd_balance < capital_usd + self.gas_fee_usd: self.withdraw_from_yield(timestamp=timestamp)
        actual = self.risk_manager.adjust_position_size(capital_usd, self.usd_balance, self.gas_fee_usd, self.risk_manager.gas_reserve_usd)
        if actual <= 0: return None
        self.usd_balance -= (actual + self.gas_fee_usd)
        btc_amt = (actual * (1.0 - self.slippage_pct)) / current_btc_price
        sid = len(self.active_shorts) + 1000
        self.active_shorts.append({"id": sid, "collateral_usd": actual, "btc_amount": btc_amt, "entry_price": current_btc_price, "open_timestamp": timestamp, "strategy": strategy})
        logger.info(f"[{timestamp.date()}] 🔴 SHORT OPENED: ${actual:.2f}")
        self._log_transaction(timestamp, f"OPEN_SHORT_{strategy}", current_btc_price, self.usd_balance, 0, 0, self._calculate_portfolio_value(current_btc_price))
        return sid

    def close_short(self, sid, current_btc_price, timestamp):
        pos = next((s for s in self.active_shorts if s['id'] == sid), None)
        if not pos: return
        pnl = (pos['entry_price'] - current_btc_price) * pos['btc_amount']
        ret = pos['collateral_usd'] + pnl - self.gas_fee_usd
        self.usd_balance += ret
        self.active_shorts.remove(pos)
        logger.info(f"[{timestamp.date()}] 🟢 SHORT CLOSED: ID {sid}. PnL: ${pnl:.2f}")
        self._log_transaction(timestamp, "CLOSE_SHORT", current_btc_price, self.usd_balance, 0, 0, self._calculate_portfolio_value(current_btc_price))

    def _check_and_harvest(self, current_price, timestamp):
        if not self.active_lps or self.usd_balance < self.gas_fee_usd: return
        refill = self.usd_balance < GAS_RESERVE_USD
        for lp in self.active_lps:
            total = lp['fees_accrued_usdt'] + (lp['fees_accrued_btc'] * current_price)
            if total > self.gas_fee_usd * (2 if refill else 25) and self.usd_balance >= self.gas_fee_usd:
                self.usd_balance -= self.gas_fee_usd
                if refill: self.usd_balance += total
                else: self.btc_hodl_balance += lp['fees_accrued_btc']; self.usd_balance += lp['fees_accrued_usdt']
                lp['fees_accrued_btc'] = lp['fees_accrued_usdt'] = 0.0

    def emergency_shutdown(self, current_price, timestamp):
        logger.critical(f"[{timestamp.date()}] 🚨 EMERGENCY SHUTDOWN 🚨")
        self.is_killed = True
        self.withdraw_from_yield(timestamp=timestamp)
        self.btc_hodl_balance += self.btc_collateral_balance
        self.btc_collateral_balance = 0.0
        for lp in list(self.active_lps): self.close_lp(lp['id'], current_price, timestamp, True)
        for s in list(self.active_shorts): self.close_short(s['id'], current_price, timestamp)
        if self.btc_hodl_balance > 0: self.sell_btc(self.btc_hodl_balance, current_price, timestamp)

    def run(self, df, strategy):
        if df.empty: return {}
        initial_btc_price, final_btc_price = df.iloc[0]['Close'], df.iloc[-1]['Close']
        for _, row in df.iterrows():
            if self.usd_balance <= 0 or self.is_liquidated: break
            current_price, timestamp = row['Close'], row['Open_time']
            current_equity = self._calculate_portfolio_value(current_price)
            if self.is_killed: self.portfolio_history.append(current_equity); continue
            if current_equity > self.global_hwm: self.global_hwm = current_equity
            self.daily_hwm_window.append((timestamp, current_equity))
            self.daily_hwm_window = [(t, v) for t, v in self.daily_hwm_window if t >= timestamp - timedelta(hours=24)]
            regime = strategy.current_regime.name if hasattr(strategy, 'current_regime') and hasattr(strategy.current_regime, 'name') else 'UNCERTAIN'
            if self.risk_manager.check_drawdown_limits(current_equity, self.global_hwm, max([v for t,v in self.daily_hwm_window]), regime) == 'KILL_SWITCH':
                self.emergency_shutdown(current_price, timestamp); self.portfolio_history.append(self._calculate_portfolio_value(current_price)); continue
            if self.total_debt_usd > 0:
                self.health_factor = self.risk_manager.calculate_health_factor(self.btc_collateral_balance * current_price, self.total_debt_usd)
                if self.risk_manager.is_liquidated(self.health_factor): self._handle_liquidation(timestamp); continue
            
            # Fix: Fraction of the YEAR for a 4h candle
            hours = int(DEFAULT_INTERVAL[:-1]) if 'h' in DEFAULT_INTERVAL else 24
            candle_fraction_of_year = (hours / 24.0) * (1.0 / 365.0)
            self.yield_manager.compound_interest(daily_fraction=candle_fraction_of_year)
            
            if self.total_debt_usd > 0: self.total_debt_usd += self.total_debt_usd * (self.loan_apy * candle_fraction_of_year)
            for lp in self.active_lps:
                if lp['range_lower'] < current_price < lp['range_upper']:
                    share = float(self._get_lp_value(lp, current_price)[0]) / row.get('TVL_USD', 1e9) # Fallback para TVL alto se faltar dado
                    lp['fees_accrued_usdt'] += self._volume_per_candle(row.get('VolumeUSD', 0)) * POOL_FEE_RATE * share
                    lp['days_out_of_range'] = 0
                else: lp['days_out_of_range'] += 1
            try: self._check_and_harvest(current_price, timestamp)
            except: pass
            strategy.execute(row, self, timestamp)
            self.portfolio_history.append(self._calculate_portfolio_value(current_price))
        return {'initial_capital_usd': self.initial_capital, 'final_usd_value': self.portfolio_history[-1], 'profit_usd': self.portfolio_history[-1] - self.initial_capital,
                'profit_percentage_usd': ((self.portfolio_history[-1] / self.initial_capital) - 1) * 100, 'btc_benchmark_final_value': (self.initial_capital / initial_btc_price) * final_btc_price,
                'backtest_start_date': str(df.iloc[0]['Open_time']), 'backtest_end_date': str(df.iloc[-1]['Open_time']), 'decision_history': self.decision_history, 'transaction_log': self.transaction_log}
