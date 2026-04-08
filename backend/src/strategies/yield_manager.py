import logging

logger = logging.getLogger(__name__)

class AaveYieldManager:
    """
    Gerenciador de Yield para Stablecoins simulando depósitos na Aave V3.
    Objetivo: Rentabilizar capital ocioso durante bear markets e períodos de incerteza.
    """
    
    def __init__(self, apy_rate: float = 0.05):
        """
        Inicializa o gerenciador.
        Args:
            apy_rate: Annual Percentage Yield (padrão 5% a.a.)
        """
        self.deposited_usd = 0.0
        self.apy_rate = apy_rate
        self.accrued_yield_usd = 0.0

    def deposit_usd(self, amount: float) -> bool:
        """Deposita USD no pool de lending."""
        if amount <= 0:
            return False
        
        self.deposited_usd += amount
        return True

    def withdraw_usd(self, amount: float = None) -> float:
        """
        Saca do pool de lending (inclui principal + yield).
        Se amount for None, saca 100%.
        """
        if amount is None or amount >= self.deposited_usd:
            # Saca tudo
            total = self.deposited_usd + self.accrued_yield_usd
            self.deposited_usd = 0.0
            self.accrued_yield_usd = 0.0
            return total
            
        # Saque parcial (simplificado, consome principal primeiro, o yield fica lá por simplicidade
        # ou consideramos proporcional. Para facilitar: saca o principal)
        self.deposited_usd -= amount
        return amount

    def compound_interest(self, daily_fraction: float = 1/365.0) -> float:
        """
        Aplica os juros compostos baseados na taxa diária.
        Deve ser chamado a cada dia ou proporção de candle.
        Returns o valor do yield gerado no período.
        """
        if self.deposited_usd <= 0:
            return 0.0
            
        period_interest = self.deposited_usd * (self.apy_rate * daily_fraction)
        self.accrued_yield_usd += period_interest
        # Composição (os juros passam a render no próximo ciclo na Aave)
        self.deposited_usd += period_interest
        self.accrued_yield_usd = 0.0 # Zeramos pois já somou no deposit_usd
        
        return period_interest

    def get_total_balance(self) -> float:
        """Retorna saldo total na Aave (principal + yield não sacado/incorporado)"""
        return self.deposited_usd + self.accrued_yield_usd
