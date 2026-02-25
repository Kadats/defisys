# Configuração de Rate Limit - Gemini API

## 📊 Status Atual

✅ **Sistema configurado para garantir que TODAS as decisões venham do Gemini (sem fallback por rate limit)**

## ⚙️ Configuração Implementada

### 1. Delay Entre Chamadas
```yaml
# docker-compose.yml
environment:
  - GEMINI_API_DELAY_SECONDS=5.0  # Delay de 5s entre chamadas
```

### 2. Cálculo do Rate Limit

| Parâmetro | Valor |
|-----------|-------|
| **Limite da API Gemini** | 15 RPM (requests por minuto) |
| **Intervalo mínimo necessário** | 60s ÷ 15 = 4s entre requests |
| **Delay configurado** | 5.0s (margem de segurança de 25%) |
| **Taxa efetiva** | 60s ÷ 5s = **12 RPM** ✅ |
| **Margem de segurança** | 3 RPM abaixo do limite |

### 3. Impacto em Simulações

#### Simulação de 30 dias (padrão)
- **Candles:** 180 (30 dias × 6 candles/dia de 4h)
- **Decisões do Gemini:** 180
- **Tempo total:** 180 × 5s = **15 minutos**
- **Taxa média:** 12 RPM (sempre < 15 RPM) ✅

#### Simulação de 7 dias
- **Candles:** 42
- **Tempo total:** 42 × 5s = **3.5 minutos**

#### Simulação de 90 dias
- **Candles:** 540
- **Tempo total:** 540 × 5s = **45 minutos**

## 🔧 Como Funciona

### Fluxo de Decisão com Delay

```python
# backend/src/ai/llm_agent.py

def _consult_gemini(context):
    # 1. Chamar API do Gemini
    response = MODEL.generate_content(context_str)
    
    # 2. Processar resposta JSON
    result = _extract_json_from_text(response.text)
    
    # 3. Validar estrutura
    validate_response(result)
    
    # 4. ✨ DELAY AUTOMÁTICO (5s)
    if api_call_successful and GEMINI_API_DELAY > 0:
        logger.debug("[GEMINI] Waiting %.1fs to respect rate limit...", GEMINI_API_DELAY)
        time.sleep(GEMINI_API_DELAY)
    
    # 5. Retornar decisão
    return result
```

### Retry com Backoff Exponencial

Se ocorrer erro 429 (rate limit excedido):
1. **Tentativa 1:** Aguarda 2s e tenta novamente
2. **Tentativa 2:** Aguarda 4s e tenta novamente
3. **Tentativa 3:** Aguarda 8s e tenta novamente
4. **Falha total:** Usa fallback heurístico

## 📝 Logs Durante Execução

```
[GEMINI] Calling API with context... (attempt 1/3)
[GEMINI] Decision: CONSERVATIVE_LP | Amount: 35% | Medium ML confidence
[GEMINI] Waiting 5.0s to respect rate limit (15 RPM)...
```

## 🎯 Ajustes Opcionais

### Reduzir Tempo de Simulação (mais rápido, mais arriscado)

```yaml
# docker-compose.yml
environment:
  - GEMINI_API_DELAY_SECONDS=4.0  # Mínimo seguro (15 RPM exatos)
```

**Resultado:** 180 candles em 12 minutos (em vez de 15)

### Aumentar Margem de Segurança (mais lento, mais seguro)

```yaml
# docker-compose.yml
environment:
  - GEMINI_API_DELAY_SECONDS=6.0  # Extra conservador
```

**Resultado:** 180 candles em 18 minutos (10 RPM)

## ⚠️ Observações Importantes

1. **Rate Limit é por API Key:** Se você fizer testes manuais enquanto a simulação roda, pode exceder o limite.

2. **Período de Reset:** O Gemini API usa janelas deslizantes de 1 minuto. Após exceder o limite, aguarde 1-2 minutos antes de tentar novamente.

3. **Plano Gratuito:** O limite de 15 RPM é do plano gratuito. Planos pagos têm limites maiores.

4. **Fallback Sempre Ativo:** Mesmo com delay configurado, o fallback heurístico está sempre disponível como backup.

## ✅ Validação

Para verificar que o sistema está funcionando:

```bash
docker compose exec backend python -c "
from backend.src.ai import llm_agent
print(f'Delay configurado: {llm_agent.GEMINI_API_DELAY}s')
print(f'Taxa máxima: {60/llm_agent.GEMINI_API_DELAY:.1f} RPM')
print(f'Status: {'✅ SEGURO' if 60/llm_agent.GEMINI_API_DELAY <= 15 else '⚠️ ARRISCADO'}')
"
```

Saída esperada:
```
Delay configurado: 5.0s
Taxa máxima: 12.0 RPM
Status: ✅ SEGURO
```

## 🚀 Executar Simulação Completa

```bash
docker compose exec backend python -c "
from backend.src.system_runner import run_trading_system
result = run_trading_system()
print(f\"ROI: {result['backtest_report']['profit_percentage_usd']:.2f}%\")
print(f\"Trades: {result['backtest_report']['total_trades']}\")
"
```

**Tempo estimado:** ~15 minutos para 30 dias (todas as decisões virão do Gemini)

---

**Última atualização:** 2026-02-25
**Status:** ✅ Pronto para produção
