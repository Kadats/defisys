## 🤖 Agentic Risk Manager - Integração Google Gemini API

### ✅ Status da Implementação

A integração do **Google Gemini 1.5 Flash** foi completada com sucesso. O sistema agora consulta uma verdadeira API LLM para tomadas de decisão de risco em vez de usar apenas heurísticas.

---

## 📋 Configuração Inicial

### Passo 1: Obter API Key do Google

1. Acesse: https://ai.google.dev/tutorials/setup
2. Clique em "Get an API key in Google AI Studio"
3. Crie um novo projeto ou selecione um existente
4. Copie a API Key gerada (começa com `AI...`)

### Passo 2: Adicionar ao `.env`

No arquivo `.env` da raiz do projeto, adicione:

```bash
GEMINI_API_KEY=sua_api_key_aqui_AIza...
```

**Exemplo:**
```bash
# .env
DATABASE_URL=postgresql://user:password@postgres:5432/defisys
GEMINI_API_KEY=AIzaSyD_xample1234567890abcdefghij
```

### Passo 3: Instalar Dependências

```bash
docker compose exec backend poetry add google-generativeai
# OU if using requirements.txt
docker compose exec backend pip install google-generativeai
```

### Passo 4: Rebuild Docker (se necessário)

```bash
docker compose build backend
docker compose up backend
```

---

## 🚀 Modo de Uso

### Usar Gemini API em Tempo Real (Sem Limite)

```bash
# Normal - usa dados de 2024-01-01 até hoje (~775 candles em 4h)
docker compose exec backend python -m backend.src.main
```

**Logs esperados:**
```
[GEMINI] Decision: BORROW_AND_LP | Amount: 50% | High ML confidence...
[2024-01-01] 🤖 AGENT DECISION: BORROW_AND_LP | Allocation: 50%
```

### Testar com Janela de 30 Dias (Evita Rate Limit)

Para testes iniciais sem exceder o **Free Tier Rate Limit (15 requisições por minuto)**:

```bash
# Usar apenas últimos 30 dias (~180 candles em 4h)
docker compose exec backend env GEMINI_BACKTEST_DAYS=30 python -m backend.src.main
```

**Logs esperados:**
```
⚠️  GEMINI_BACKTEST_DAYS=30: Limiting backtest to last 30 days...
2026-02-23 18:00:00 - 2026-03-25 18:00:00 (~180 candles)
[GEMINI] Decision: SPOT_ONLY | Amount: 25%
```

### Se Gmini API Não Disponível - Fallback Automático

Se a API estiver indisponível, o sistema automaticamente retorna para **decision-making heurístico**:

```
[GEMINI] API Error: RateLimitError: Rate limit exceeded
[FALLBACK] Using heuristic decision logic (Gemini API unavailable)
[2024-01-01] SPOT_ONLY: Low ML confidence (45%)
```

---

## 📊 Limites de Rate

### Google Gemini Free Tier

| Métrica | Limite |
|---------|--------|
| **Requests por minuto** | 15 RPM |
| **Tokens por minuto** | 1M |
| **Requests por dia** | 1.500 |

### Como Respeitar Limites

1. **GEMINI_BACKTEST_DAYS=30** - Usa apenas 180 candles (~180 requisições)
2. **GEMINI_BACKTEST_DAYS=90** - ~540 candles (~540 requisições) - OK
3. **Sem limite** - ~775 candles (~775 requisições) - OK (menos de 1.500/dia)

⚠️ **Nota:** Se carregar 2+ anos de dados (~4.700 candles), use ambiente separado ou premium.

---

## 🔍 Monitoramento e Debugging

### Ver Logs do Gemini

```bash
# Execute dentro do container e grep por GEMINI
docker compose exec backend python -m backend.src.main 2>&1 | grep -i gemini
```

### Exemplos de Log Esperados

**Sucesso com Gemini:**
```
[GEMINI] API configured successfully with gemini-1.5-flash
[GEMINI] Decision: BORROW_AND_LP | Amount: 50% | High ML confidence (78%) + safe HF (2.34)
[2024-01-01] 🤖 AGENT DECISION: BORROW_AND_LP | Allocation: 50%
```

**Fallback por Rate Limit:**
```
[GEMINI] API Error: RateLimitError: ...exceeds rate limit...
[FALLBACK] Using heuristic decision logic (Gemini API unavailable)
```

**Fallback por JSON Inválido:**
```
[GEMINI] JSON Decode Error: ...invalid JSON...
[FALLBACK] Using heuristic decision logic (Gemini API unavailable)
```

---

## 🛠️ Estrutura Técnica

### Fluxo de Decisão

```
┌─────────────────────┐
│  Contexto de Mercado │  (RSI, HF, ML Confidence, USD, BTC, Debt)
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ Gemini API   │ ──JSON Mode──▶ {"action": "...", "amount_pct": 0.x, ...}
    └──┬───────────┘
       │
       ├─ Sucesso? ──▶ Retorna JSON estruturado
       │
       └─ Erro/Rate Limit? ──▶ Fallback para heurísticas
           (15+ requisições/min, timeout, etc)
           ▼
    ┌──────────────────┐
    │ Heurística Legada│  (8 tiers baseado em RSI/HF/ML)
    └──────────────────┘
           │
           ▼
    ┌──────────────┐
    │ Roteamento   │──▶ Execute ação (SPOT_ONLY, BORROW_AND_LP, etc)
    └──────────────┘
```

### Forçar JSON Mode

No arquivo `llm_agent.py`, a resposta é forçada para JSON usando:

```python
response = MODEL.generate_content(
    context_str,
    generation_config={
        "response_mime_type": "application/json",  # ← Força JSON puro
        "temperature": 0.3,  # ← Baixa temperatura para consistência
    },
)
```

### Validação de Resposta

```python
# 1. Parse JSON
result = json.loads(response_text)

# 2. Validar campos
action in {"SPOT_ONLY", "BORROW_AND_LP", "CONSERVATIVE_LP", "DEFENSE_MODE", "DO_NOTHING"}
amount_pct ∈ [0.0, 1.0]  # Clamp if needed

# 3. Se falhar, usar heurísticas
```

---

## 📝 System Prompt (Alma do Agente)

O agente é instruído com um **System Prompt rigoroso** que define seu papel como "Expert DeFi Risk Manager".

**Trechos-chave:**

```
"If health_factor < 1.25: Choose DEFENSE_MODE (critical liquidation risk)."
"If ML > 0.75 and HF > 2.0: Choose BORROW_AND_LP (high confidence, safe to leverage)."
"If 0.60 < ML <= 0.75 and HF > 1.8: Choose CONSERVATIVE_LP (medium confidence, moderate risk)."
```

O prompt está em `backend/src/ai/llm_agent.py` variável `SYSTEM_PROMPT`.

---

## ✅ Checklist de Implantação

- [x] Adicionar `google-generativeai` ao `pyproject.toml`
- [x] Configurar `GEMINI_API_KEY` no `docker-compose.yml`
- [x] Implementar `_consult_gemini()` com JSON Mode
- [x] Implementar `_fallback_decision()` para robustez
- [x] Adicionar `GEMINI_BACKTEST_DAYS` para limitar janelas
- [x] Atualizar `system_runner.py` para respeitar limite de dias
- [x] Testar com casos de sucesso e falha
- [ ] Monitorar PnL com decisões do Gemini vs Heurísticas
- [ ] Implementar cache de respostas (Phase 2)
- [ ] Multi-model ensemble (GPT-4, Claude) (Phase 2)

---

## 🐛 Troubleshooting

### "GEMINI_API_KEY not found in environment"

```bash
# Solução: Adicione no .env e rebuild
docker compose build backend
docker compose up backend
```

### "rate limit exceeded. Please retry after X seconds"

```bash
# Solução: Use GEMINI_BACKTEST_DAYS=30 ou 60
docker compose exec backend env GEMINI_BACKTEST_DAYS=30 python -m backend.src.main
```

### "Invalid JSON in response"

```bash
# Gemini às vezes retorna markdown code blocks
# Já tratado em llm_agent.py na função _consult_gemini()
# Se persistir, aumentar temperature ou clarificar prompt
```

### Testando Localmente (sem Docker)

```bash
# 1. Instalar dependências
pip install google-generativeai

# 2. Exportar API key
export GEMINI_API_KEY=AIza...

# 3. Testar função
python -c "
from backend.src.ai.llm_agent import consult_risk_agent
result = consult_risk_agent({'rsi': 50, 'health_factor': 2.0, 'ml_confidence': 0.75})
print(result)
"
```

---

## 📚 Referências

- [Google AI Studio](https://ai.google.dev)
- [Gemini API Docs](https://ai.google.dev/tutorials/python_quickstart)
- [JSON Mode Docs](https://ai.google.dev/api/rest/v1beta/generativeai.models/generateContent)
- [Rate Limits](https://ai.google.dev/pricing#api)

---

## 🎯 Próximas Etapas (Phase 2-3)

1. **Implementar Cache**
   - Armazenar respostas do Gemini em Redis
   - Economizar quota consumindo cache para contextos similares

2. **Multi-Agent Ensemble**
   - Consultar Gemini + Claude + GPT-4
   - Votação consensual para maior robustez

3. **Feedback Loop**
   - Rastrear PnL de cada decision
   - Fine-tune do system prompt baseado em performance

4. **Monitoring Dashboard**
   - Exibir "Gemini Confidence vs Heuristic Confidence"
   - Rastrear uso de API (requisições/dia, tokens)
   - Alertas para rate limit approaching
