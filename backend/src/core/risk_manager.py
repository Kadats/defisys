"""
Risk Management System for DeFi Trading.

Provides centralized risk assessment and safety checks for leveraged positions.
Handles health factor monitoring, gas solvency, and emergency conditions.
"""
import logging
from typing import Literal, Tuple

from ..config import TARGET_RESERVE_RATIO

logger = logging.getLogger(__name__)

# Health Factor risk management thresholds
HF_WARNING_THRESHOLD = 1.3
HF_CRITICAL_THRESHOLD = 1.1
HF_REFINANCE_THRESHOLD = 2.0

# Liquidation parameters
LIQUIDATION_THRESHOLD = 0.80
LIQUIDATION_PENALTY = 0.10

# Gas and solvency thresholds
EMERGENCY_GAS_MULTIPLIER = 0.5  # Trigger emergency when balance < 50% of gas reserve


HealthStatus = Literal['SAFE', 'WARNING', 'CRITICAL', 'LIQUIDATION']


class RiskManager:
    """
    Manages risk assessment and safety checks for leveraged DeFi positions.
    
    Responsibilities:
    - Health factor monitoring and classification
    - Gas solvency checks (ensure enough USD for transaction fees)
    - Emergency condition detection
    - Risk threshold enforcement
    """
    
    def __init__(
        self,
        gas_reserve_usd: float,
        simulated_gas_fee_usd: float,
        hf_warning: float = HF_WARNING_THRESHOLD,
        hf_critical: float = HF_CRITICAL_THRESHOLD,
        hf_refinance: float = HF_REFINANCE_THRESHOLD,
        liquidation_threshold: float = LIQUIDATION_THRESHOLD
    ):
        """
        Initialize the Risk Manager.
        
        Args:
            gas_reserve_usd: Minimum USD balance to keep for gas fees
            simulated_gas_fee_usd: Cost of a single transaction
            hf_warning: HF threshold for warning state (default 1.3)
            hf_critical: HF threshold for critical state (default 1.1)
            hf_refinance: Minimum HF to allow refinancing (default 2.0)
            liquidation_threshold: LTV ratio for liquidation (default 0.8)
        """
        self.gas_reserve_usd = gas_reserve_usd
        self.simulated_gas_fee_usd = simulated_gas_fee_usd
        self.hf_warning = hf_warning
        self.hf_critical = hf_critical
        self.hf_refinance = hf_refinance
        self.liquidation_threshold = liquidation_threshold
        
        logger.info(
            f"RiskManager initialized: GAS_RESERVE=${gas_reserve_usd:.2f}, "
            f"HF_WARNING={hf_warning}, HF_CRITICAL={hf_critical}, HF_REFINANCE={hf_refinance}"
        )
    
    def calculate_health_factor(self, collateral_value: float, debt: float) -> float:
        """
        Calculate the health factor for a leveraged position.
        
        Args:
            collateral_value: Total collateral value in USD
            debt: Total debt amount in USD
        
        Returns:
            Health factor (HF > 1.0 is safe, HF <= 1.0 triggers liquidation)
        """
        if debt <= 0:
            return 999.0  # Arbitrarily high number for no debt
        
        return (collateral_value * self.liquidation_threshold) / debt
    
    def check_health_status(
        self, 
        collateral_value: float, 
        debt: float
    ) -> Tuple[HealthStatus, float]:
        """
        Assess the health status of a leveraged position.
        
        Args:
            collateral_value: Total collateral value in USD
            debt: Total debt amount in USD
        
        Returns:
            Tuple of (status, health_factor)
            - 'SAFE': HF > warning threshold
            - 'WARNING': warning threshold >= HF > critical threshold
            - 'CRITICAL': critical threshold >= HF > 1.0
            - 'LIQUIDATION': HF <= 1.0
        """
        hf = self.calculate_health_factor(collateral_value, debt)
        
        if hf <= 1.0:
            return 'LIQUIDATION', hf
        elif hf < self.hf_critical:
            return 'CRITICAL', hf
        elif hf < self.hf_warning:
            return 'WARNING', hf
        else:
            return 'SAFE', hf
    
    def can_afford_gas(self, balance: float) -> bool:
        """
        Check if the balance is sufficient to pay a single gas fee.
        
        Args:
            balance: Current USD balance
        
        Returns:
            True if balance >= simulated_gas_fee_usd
        """
        return balance >= self.simulated_gas_fee_usd
    
    def should_emergency_close(self, balance: float) -> bool:
        """
        Determine if an emergency LP close is needed due to gas solvency.
        
        Emergency close is triggered when the USD balance falls below a critical
        threshold (50% of gas reserve), but still has enough for one gas payment.
        This prevents the "deadlock" where we can't close positions due to lack of gas.
        
        Args:
            balance: Current USD balance
        
        Returns:
            True if emergency close should be attempted
        """
        emergency_threshold = self.gas_reserve_usd * EMERGENCY_GAS_MULTIPLIER
        return balance < emergency_threshold and self.can_afford_gas(balance)
    
    def can_refinance(self, health_factor: float) -> bool:
        """
        Check if the position is healthy enough to allow refinancing (new borrows).
        
        Args:
            health_factor: Current health factor
        
        Returns:
            True if HF > refinance threshold
        """
        return health_factor > self.hf_refinance
    
    def is_liquidated(self, health_factor: float) -> bool:
        """
        Check if the position should be liquidated.
        
        Args:
            health_factor: Current health factor
        
        Returns:
            True if HF <= 1.0
        """
        return health_factor <= 1.0
    
    def calculate_safe_balance(self, total_balance: float) -> float:
        """
        Calculate the balance available for operations after reserving gas.
        
        Args:
            total_balance: Total USD balance
        
        Returns:
            Safe balance (total - gas reserve), minimum 0.0
        """
        return max(0.0, total_balance - self.gas_reserve_usd)

    def calculate_target_reserve(self, total_equity_usd: float) -> float:
        """Compute dynamic reserve target as a fraction of total equity."""
        return total_equity_usd * TARGET_RESERVE_RATIO
    
    def assess_rebalance_options(
        self,
        health_factor: float,
        balance: float,
        has_active_lps: bool,
        deleverage_threshold: float = 1.6
    ) -> dict:
        """
        Assess available rebalancing options based on current state.
        
        V13 Smart Reserve Logic:
        - Priority 1: Use reserve cash to pay debt if HF < deleverage_threshold
        - Priority 2: Only close LP if cash is exhausted AND HF < critical threshold
        
        Args:
            health_factor: Current health factor
            balance: Current USD balance
            has_active_lps: Whether there are active LP positions
            deleverage_threshold: HF threshold to trigger cash-based deleveraging (default 1.6)
        
        Returns:
            Dict with rebalancing recommendations:
            - 'action': 'none', 'pay_debt_with_cash', 'close_lp', 'emergency_close'
            - 'reason': Explanation for the recommended action
            - 'available_cash': Amount of cash available for rebalancing
        """
        if health_factor >= self.hf_warning:
            return {
                'action': 'none',
                'reason': 'Health factor is safe',
                'available_cash': 0.0
            }

        # Check for emergency gas solvency issue first
        if self.should_emergency_close(balance) and has_active_lps:
            return {
                'action': 'emergency_close',
                'reason': f'USD balance ${balance:.2f} below emergency threshold (${self.gas_reserve_usd * EMERGENCY_GAS_MULTIPLIER:.2f})',
                'available_cash': 0.0
            }

        available_cash = self.calculate_safe_balance(balance)

        # Defense 1: If HF deteriorates, use any available USD to pay debt
        if health_factor < deleverage_threshold and available_cash > 0:
            return {
                'action': 'pay_debt_with_cash',
                'reason': f'HF={health_factor:.2f} below {deleverage_threshold}, using cash to defend position',
                'available_cash': available_cash
            }

        # Defense 2: If HF is critical and wallet is empty, close LP to raise cash
        if health_factor < self.hf_warning and has_active_lps and available_cash <= 0:
            return {
                'action': 'close_lp',
                'reason': f'HF={health_factor:.2f} critical and no USD available, closing LP to raise cash',
                'available_cash': 0.0
            }

        return {
            'action': 'none',
            'reason': 'No defensive action required',
            'available_cash': 0.0
        }
