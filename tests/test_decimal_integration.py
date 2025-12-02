#!/usr/bin/env python3
"""
Script de validação para testar a integração Decimal no TradingEngine.
Verifica que valores float do engine são convertidos corretamente para Decimal
nas funções matemáticas do Uniswap, evitando TypeErrors.
"""

from decimal import Decimal
from backend.src.utils.math.uniswap import calculate_lp_value, calculate_liquidity_l

def test_decimal_conversions():
    """Testa conversões automáticas de float -> Decimal."""
    
    print("=" * 70)
    print("TESTE: Validação de Integração Decimal no Uniswap Math")
    print("=" * 70)
    
    # Parâmetros de teste (valores reais de mercado)
    capital_usd = 1000.0  # float (como vem do TradingEngine)
    range_lower = 85000.0
    range_upper = 105000.0
    current_price = 95000.0
    
    print("\n1. Testando calculate_liquidity_l com valores float...")
    print(f"   Capital: ${capital_usd:,.2f}")
    print(f"   Range: ${range_lower:,.2f} - ${range_upper:,.2f}")
    print(f"   Preço atual: ${current_price:,.2f}")
    
    try:
        L, amount_btc, amount_usdt = calculate_liquidity_l(
            capital_usd=capital_usd,
            range_lower=range_lower,
            range_upper=range_upper,
            current_price=current_price
        )
        
        print(f"\n   ✅ SUCESSO!")
        print(f"   Liquidity L: {L}")
        print(f"   Amount BTC: {amount_btc}")
        print(f"   Amount USDT: {amount_usdt}")
        print(f"   Tipos: L={type(L)}, BTC={type(amount_btc)}, USDT={type(amount_usdt)}")
        
        # Verificar que retorna Decimal
        assert isinstance(L, Decimal), "L deve ser Decimal"
        assert isinstance(amount_btc, Decimal), "amount_btc deve ser Decimal"
        assert isinstance(amount_usdt, Decimal), "amount_usdt deve ser Decimal"
        
    except TypeError as e:
        print(f"\n   ❌ ERRO: {e}")
        return False
    
    print("\n2. Testando calculate_lp_value com valores float...")
    
    try:
        total_value, btc, usdt = calculate_lp_value(
            liquidity=float(L),  # Simula como vem do dict LP no engine
            range_lower=range_lower,
            range_upper=range_upper,
            current_price=current_price
        )
        
        print(f"\n   ✅ SUCESSO!")
        print(f"   Total Value: ${total_value}")
        print(f"   Amount BTC: {btc}")
        print(f"   Amount USDT: ${usdt}")
        print(f"   Tipos: value={type(total_value)}, BTC={type(btc)}, USDT={type(usdt)}")
        
        # Verificar que retorna Decimal
        assert isinstance(total_value, Decimal), "total_value deve ser Decimal"
        assert isinstance(btc, Decimal), "btc deve ser Decimal"
        assert isinstance(usdt, Decimal), "usdt deve ser Decimal"
        
    except TypeError as e:
        print(f"\n   ❌ ERRO: {e}")
        return False
    
    print("\n3. Testando operações mistas (Decimal + float)...")
    
    try:
        # Simula o que acontece no TradingEngine
        fees_btc = 0.001  # float
        fees_usdt = 50.0  # float
        
        # Cálculo de valor com fees (como no close_lp)
        fees_value = fees_usdt + (fees_btc * current_price)
        
        # Conversão explícita para float antes de somar (como fizemos no engine)
        final_value = float(total_value) + fees_value
        
        print(f"\n   ✅ SUCESSO!")
        print(f"   Fees BTC em USD: ${fees_btc * current_price:,.2f}")
        print(f"   Fees USDT: ${fees_usdt:,.2f}")
        print(f"   Valor final: ${final_value:,.2f}")
        
    except TypeError as e:
        print(f"\n   ❌ ERRO: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 70)
    print("\nA integração Decimal está funcionando corretamente.")
    print("O TradingEngine pode passar valores float para as funções")
    print("matemáticas do Uniswap sem causar TypeErrors.\n")
    
    return True


if __name__ == "__main__":
    success = test_decimal_conversions()
    exit(0 if success else 1)
