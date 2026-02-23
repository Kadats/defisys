## 📐 Arquitetura: Mock vs Google Gemini API

### ANTES: Arquitetura Mock-Only

```
┌─────────────────────────────────────────────────────────────┐
│ Market Data (Open, Close, RSI, etc)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ ML Prediction Model (XGBoost)  │
         │ Output: confidence (0.0-1.0)   │
         └───────────────┬───────────────┘
                         │
                         ▼
      ┌──────────────────────────────────────┐
      │ AccumulatorStrategy.execute()         │
      │ - Checks defense mode                │
      │ - Checks cool-down                   │
      │ - Analyzes market entry              │
      └────────────────┬─────────────────────┘
                       │
                       ▼
          ┌────────────────────────────────┐
          │ llm_agent (MOCK)               │
          │ ❌ Determinístico (8 tiers)   │
          │ ❌ Hardcoded rules             │
          │ ❌ Sem LLM inteligência       │
          └────────────┬───────────────────┘
                       │
                       ▼
        Decision: {action, amount_pct, reason}
        
        Examples:
        ├─ DEFENSE_MODE
        ├─ BORROW_AND_LP
        ├─ CONSERVATIVE_LP
        ├─ SPOT_ONLY
        └─ DO_NOTHING
                       │
                       ▼
      ┌──────────────────────────────────────┐
      │ Route to Execution Function:         │
      │ ├─ _execute_bull_entry()             │
      │ ├─ _execute_defense_mode()           │
      │ ├─ _open_lp_conservative()           │
      │ ├─ _simple_spot_buy()                │
      │ └─ _maintain_positions()             │
      └──────────────────────────────────────┘
           │
           ▼
    Positions Executed ✅
```

**Problemas:**
- ❌ Lógica hardcoded e inflexível
- ❌ Sem aprendizado contextual
- ❌ Não adapta a novas situações de mercado
- ❌ Engessado em if/else

---

### DEPOIS: Arquitetura com Google Gemini API

```
┌─────────────────────────────────────────────────────────────┐
│ Market Data (Open, Close, RSI, etc) + Portfolio State       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │ ML Prediction Model (XGBoost)  │
         │ Output: confidence (0.0-1.0)   │
         └───────────────┬───────────────┘
                         │
                         ▼
      ┌──────────────────────────────────────┐
      │ AccumulatorStrategy.execute()         │
      │ - Checks defense mode                │
      │ - Checks cool-down                   │
      │ - Builds agent context (5 fields)    │
      └────────────────┬─────────────────────┘
                       │
                       ▼
           ┌─────────────────────────────┐
           │ consult_risk_agent()        │
           │ (Main Orchestrator)         │
           └────────┬────────────────────┘
                    │
                    ├─ API disponível? SIM
                    │  │
                    │  ▼
                    │  ┌──────────────────────────────────┐
                    │  │ _consult_gemini()               │
                    │  │ ✅ Chama Google Gemini API      │
                    │  │ ✅ JSON Mode forçado            │
                    │  │ ✅ System Prompt rigoroso       │
                    │  │ ✅ Exception handling robusto   │
                    │  └──────────┬───────────────────────┘
                    │             │
                    │             ├─ Sucesso?
                    │             │  │ ✅ JSON válido
                    │             │  │ ✅ Action em WHITE-LIST
                    │             │  │ ✅ amount_pct ∈ [0, 1]
                    │             │  └──▶ Retorna decisão
                    │             │
                    │             └─ Erro? (JSON, Rate Limit, Timeout)
                    │                └──▶ Fallback automático
                    │
                    ├─ API indisponível? NÃO
                    │  │
                    │  ▼
                    └─ ┌──────────────────────────────────┐
                       │ _fallback_decision()             │
                       │ ✅ Heurísticas (8 tiers)        │
                       │ ✅ Determinístico               │
                       │ ✅ Sempre válido                │
                       └────────────┬─────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────────┐
                    │ Decision Output                  │
                    │ {                                │
                    │   "action": "...",               │
                    │   "amount_pct": 0.x,             │
                    │   "reason": "..."                │
                    │ }                                │
                    │                                  │
                    │ [GEMINI]  ou  [FALLBACK]         │
                    └────────────┬─────────────────────┘
                                 │
                                 ▼
      ┌──────────────────────────────────────────┐
      │ Route to Execution Function:             │
      │ - if action == "BORROW_AND_LP"           │
      │   └─ _execute_bull_entry()               │
      │ - elif action == "DEFENSE_MODE"          │
      │   └─ _execute_defense_mode()             │
      │ - elif action == "CONSERVATIVE_LP"       │
      │   └─ _open_lp_conservative()             │
      │ - elif action == "SPOT_ONLY"             │
      │   └─ _simple_spot_buy()                  │
      │ - elif action == "DO_NOTHING"            │
      │   └─ _maintain_positions()               │
      └──────────────────────────────────────────┘
           │
           ▼
    Positions Executed ✅
    (backed by LLM intelligence or heuristics)
```

**Melhorias:**
- ✅ Gemini API toma decisões inteligentes
- ✅ System Prompt define comportamento
- ✅ Fallback automático se API falhar
- ✅ Logging estruturado [GEMINI] vs [FALLBACK]
- ✅ Rate limit respeitado com GEMINI_BACKTEST_DAYS
- ✅ 100% backward compatible
- ✅ Pronto para multi-model ensemble (Phase 2)

---

## 🔄 Fluxo de Decisão com Fallback

```
User inicia backtest
     │
     ▼
Cada candle do backtest:
     │
     ├─ Checar DEFENSE MODE (HF < 1.5)?
     │  └─ SIM → Executar defense, skip agent
     │  └─ NÃO → Continuar
     │
     ├─ Checar COOL-DOWN (12h desde última trade)?
     │  └─ NÃO passado → skip agent, manter posições
     │  └─ SIM passado → Continuar
     │
     ├─ Montar contexto da carteira
     │  ├─ usd_balance
     │  ├─ btc_collateral
     │  ├─ aave_debt
     │  ├─ health_factor
     │  ├─ ml_confidence
     │  └─ rsi
     │
     ├─ Chamar consult_risk_agent(context)
     │  │
     │  └─ Tentar Gemini API:
     │     ├─ SUCESSO (✅ JSON válido)
     │     │  └─ [GEMINI] Decision: BORROW_AND_LP | 50%
     │     │
     │     ├─ FALHA (❌ JSON inválido)
     │     │  └─ [FALLBACK] JSON Decode Error
     │     │
     │     ├─ RATE LIMIT (❌ 15 RPM excedido)
     │     │  └─ [FALLBACK] Rate Limit Error
     │     │
     │     └─ TIMEOUT (❌ timeout > 30s)
     │        └─ [FALLBACK] Timeout Error
     │
     ├─ Receber {action, amount_pct, reason}
     │
     ├─ Rotear ação:
     │  ├─ BORROW_AND_LP → bull entry com leverage
     │  ├─ CONSERVATIVE_LP → LP sem agressividade
     │  ├─ SPOT_ONLY → compra spot simples
     │  ├─ DEFENSE_MODE → close LPs + repay debt
     │  └─ DO_NOTHING → manter posições
     │
     ▼
Executar trade + Logar resultado
     │
     ▼
Próximo candle...
```

---

## 📊 Diferenças Técnicas

| Aspecto | Mock | Gemini API |
|---------|------|-----------|
| **Decisão baseada em** | 8 tiers hardcoded | LLM contextual |
| **Qualidade de decisão** | Heurística fixa | Adaptativa ao prompt |
| **Tempo por decisão** | < 1ms | ~1-2s |
| **Requisições à API** | 0 | 1 por candle |
| **Rate limit** | N/A | 15 RPM (respeitado) |
| **Se falhar** | N/A | Fallback automático |
| **Customização** | Editar código | Editar system prompt |
| **Aprendizado** | Nenhum | Pode ser fine-tuned |
| **Multi-model** | Não | Pronto para ensemble |

---

## 🎯 Casos de Uso

### Caso 1: Mercado Bullish com Alta Confiança

```
Input:
  RSI: 55
  Health Factor: 2.5
  ML Confidence: 82%
  USD Balance: $5,000
  
MOCK Decision:
  Action: BORROW_AND_LP
  Reason: ML > 0.75 AND HF > 2.0 (tier 5)
  
GEMINI Decision:
  Action: BORROW_AND_LP
  Reason: "High ML confidence (82%) + safe HF (2.50). 
           Favorable risk/reward for full DeFi leverage."
  Amount: 0.50 (50%)
  
Resultado:
  ✅ Ambos chegam no mesmo action
  ✅ Gemini oferece contexto melhor
  ✅ Allocation pode ser mais preciso
```

### Caso 2: Mercado Oversold sem Clear Signal

```
Input:
  RSI: 28
  Health Factor: 1.9
  ML Confidence: 45%
  
MOCK Decision:
  Action: SPOT_ONLY
  Reason: RSI < 30 (tier 3)
  Amount: 0.25 (25%)
  
GEMINI Decision (possível variação):
  Action: SPOT_ONLY
  Reason: "Extreme oversold (RSI=28) but low ML 
           confidence. Accumulate cautiously."
  Amount: 0.15 (15%) [MAIS CONSERVADOR]
  
Vantagem:
  ✅ Gemini pode adaptar allocation baseado em contexto
  ✅ Pode considerar USD balance disponível
```

### Caso 3: API Indisponível (Rate Limit)

```
Tentativa: A 16ª requisição num minuto

GEMINI:
  ❌ RateLimitError: "Rate limit exceeded"
  
Fallback automático:
  ✅ _fallback_decision() ativado
  ✅ Retorna decisão via heurísticas
  ✅ Backtest continua sem quebrar
  ✅ Log: [FALLBACK] Using heuristic decision logic
```

---

## 🚀 Phase 2: Multi-Model Ensemble (Futuro)

```
Client Context
     │
     ├─ Consultar Gemini
     ├─ Consultar Claude (via API)
     ├─ Consultar GPT-4 (via OpenRouter)
     │
     └─ Voting/Consensus
        ├─ 3/3 concordam → Action com confiança 100%
        ├─ 2/3 concordam → Action com confiança 70%
        ├─ Discordam → Usar Conservative Decision
        │
        ▼
     Decision final com "Model Confidence" métrica
```

---

## 📚 Documentação Relacionada

- [GEMINI_API_SETUP.md](GEMINI_API_SETUP.md) - How to setup
- [GEMINI_IMPLEMENTATION_SUMMARY.md](GEMINI_IMPLEMENTATION_SUMMARY.md) - Technical details
- [AGENTIC_RISK_MANAGER_SUMMARY.md](AGENTIC_RISK_MANAGER_SUMMARY.md) - Original mock design
