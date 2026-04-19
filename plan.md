# Plano de Fechamento 100% (Auditoria + Review)

Data: 2026-04-19  
Contexto: este plano consolida o que faltou concluir após a auditoria fase a fase e os findings de revisão (P1 e P2), para execução disciplinada até 100%.

---

## 1) Findings obrigatórios da revisão

### P1 (bloqueante): regressão no proxy Frontend -> Backend
**Problema**
- Em `frontend/src/lib/backendEndpoints.ts`, a função `stripApiV1` remove `/api/v1` inteiro.
- Com `API_BASE_URL=http://backend:8000/api/v1`, rotas BFF passam a chamar `http://backend:8000/system/...` em vez de `http://backend:8000/api/system/...`.
- Impacto: Control Center cai em fallback (503/offline) mesmo com backend saudável.

**Ações**
1. Corrigir construção de URL para preservar prefixo `/api`.
2. Validar chamadas BFF:
- `/api/system/health` -> backend `/api/system/health`
- `/api/system/indicators` -> backend `/api/system/indicators`
- `/api/system/logs` -> backend `/api/system/logs`
- `/api/sandbox/run` -> backend `/api/sandbox/run`
3. Adicionar teste de contrato para o builder de endpoint (unitário no frontend) e/ou smoke de proxy.

**Critério de aceite**
- Sem fallback 503 quando backend está online.
- Rotas acima retornam status correto via BFF no Docker.

---

### P2 (governança): estado de planejamento marcando 100% sem evidência
**Problema**
- `.planning/STATE.md` e `.planning/ROADMAP.md` indicam 100%, mas vários `PLAN/SUMMARY/notes` ainda têm template/placeholders (`[Title]`, `[Criterion]`, `draft-initial`, checklists em aberto).
- Impacto: falsa prontidão e perda de rastreabilidade.

**Ações**
1. Rebaixar estado para refletir situação real (fases concluídas/parciais/pendentes).
2. Atualizar `PLAN.md`/`SUMMARY.md` de cada fase com evidência concreta:
- arquivos alterados
- decisões tomadas
- comandos executados
- resultados reais de teste
3. Remover placeholders remanescentes.
4. Marcar checklists de contexto com status real (feito/parcial/pendente).

**Critério de aceite**
- Nenhum `PLAN/SUMMARY` com placeholder.
- Nenhum `draft-initial` em artefato considerado “concluído”.
- `STATE.md` coerente com evidência de código/testes.

---

## 2) Pendências por fase (0 a 9)

## Fase 0 — Congelamento, baseline e inventário
**Status atual**: parcial documental.  
**Falta**
- Consolidar baseline final sem placeholders no `00-01-PLAN.md` e `00-01-SUMMARY.md`.
- Fechar notes da fase com status final (não `draft-initial`).

**Saída esperada**
- Resumo factual da baseline congelada e links para evidências reais.

---

## Fase 1 — Contratos de domínio e modelo de sistema
**Status atual**: parcial documental.  
**Falta**
- Formalizar contratos finais usados no código atual.
- Atualizar `01-01-SUMMARY.md` com artefatos reais.

**Saída esperada**
- Contratos e modelo de sistema coerentes com o que está em `backend/src`.

---

## Fase 2 — Extração do núcleo puro (risco/portfolio/estratégia)
**Status atual**: parcial técnico + parcial documental.  
**Já existe**
- `backend/src/domain/risk/manager.py`.

**Falta**
- Fechar escopo de portfolio/estratégia conforme contexto da fase (ou registrar explicitamente o recorte aceito).
- Completar `02-01-PLAN/SUMMARY` sem template.
- Garantir cobertura de testes para fronteiras do núcleo extraído.

**Saída esperada**
- Delimitação clara: o que foi extraído, o que ficou legado, e por quê.

---

## Fase 3 — Casos de uso da aplicação
**Status atual**: parcial técnico + parcial documental.  
**Já existe**
- `backend/src/application/use_cases.py`.

**Falta**
- Ampliar/confirmar uso dos casos de uso como orquestração principal.
- Atualizar plano/resumo com evidência de integração real.

**Saída esperada**
- `api.py` consumindo aplicação com fronteiras explícitas e documentadas.

---

## Fase 4 — Persistência e integrações externas
**Status atual**: pendente/parcial baixo.  
**Falta**
- Estruturar camada de persistência por repositórios/adaptadores.
- Definir gateways de integrações externas de forma consistente.
- Fechar plano/resumo e checklists da fase com execução real.

**Saída esperada**
- Fronteiras de infra claras, sem vazamento para domínio/aplicação.

---

## Fase 5 — Reescrita da API e WebSockets
**Status atual**: parcial técnico + parcial documental.  
**Já existe**
- Extração de websockets para `backend/src/interfaces/api/websocket_routes.py`.

**Falta**
- Continuar fatiamento de `backend/src/api.py` para reduzir concentração.
- Consolidar contratos de rota e compatibilidade com evidência.

**Saída esperada**
- `api.py` como composição de routers (não concentrador de regra).

---

## Fase 6 — Reconcialiação frontend e BFF
**Status atual**: parcial com regressão aberta (P1).  
**Já existe**
- Centralização de endpoints no frontend (`frontend/src/lib/backendEndpoints.ts`).

**Falta**
- Corrigir regressão de prefixo `/api` (P1).
- Completar validação BFF/estado degradado sem mascarar erro.
- Finalizar documentação de compatibilidade.

**Saída esperada**
- BFF estável e coerente com contratos do backend.

---

## Fase 7 — Estratégia de testes
**Status atual**: boa execução técnica, fechamento documental pendente.  
**Já existe**
- Markers em `pyproject.toml`.
- Smokes em `tests/smoke/test_api_smoke_contracts.py`.

**Falta**
- Consolidar artefatos de fase (plan/summary) com comandos e resultados reais.
- Opcional recomendado: separar execução por suite (`-m smoke`, `-m unit`, etc.) no fluxo oficial.

**Saída esperada**
- Gate de qualidade reproduzível e rastreável.

---

## Fase 8 — Paper runtime operacional
**Status atual**: parcial avançado técnico + pendência documental/checklist.  
**Já existe**
- `backend/src/services/paper_runtime.py`
- `backend/src/interfaces/api/paper_runtime_routes.py`
- smoke de runtime paper.

**Falta**
- Fechar checklist de readiness da fase com evidências.
- Confirmar semântica operacional completa (eventos/alertas/bloqueios) nos artefatos da fase.

**Saída esperada**
- Runtime paper auditável e oficialmente separado de backtest/sandbox.

---

## Fase 9 — Cutover, limpeza e aposentadoria do legado
**Status atual**: parcial.  
**Já existe**
- Ajustes em README/AGENTS/Makefile.

**Falta**
- Plano de cutover executável com rollback real por onda.
- Aposentadoria explícita de compatibilidades legadas pendentes.
- Fechamento de artefatos finais sem placeholder.

**Saída esperada**
- Estado final coerente entre código, operação e documentação.

---

## 3) Backlog de execução imediata (ordem recomendada)

1. Corrigir P1 e validar BFF no Docker.
2. Corrigir P2: rebaixar estado e normalizar `PLAN/SUMMARY` por fase.
3. Fechar Fase 4 (principal lacuna técnica).
4. Concluir fatiamento de Fase 5 e estabilizar Fase 6.
5. Finalizar fechamento documental de Fases 0-3, 7-9 com evidência real.

---

## 4) Evidências mínimas por fase para marcar “concluída”

- Arquivos alterados listados explicitamente.
- Decisões técnicas registradas (sem placeholders).
- Testes executados com comando real + resultado.
- Riscos/resíduos conhecidos documentados.
- Checklist da fase sem itens ambíguos.

---

## 5) Validação padrão (Docker-only)

Comando base de regressão/smoke:

```bash
docker compose --profile test run --rm -e PYTHONPATH=/app backend-test pytest -q \
  tests/smoke/test_api_smoke_contracts.py \
  tests/smoke/test_paper_runtime_smoke.py \
  tests/test_control_center_api.py \
  tests/test_api.py \
  tests/test_application_use_cases.py \
  tests/test_api_schemas.py
```

Regra:
- Não considerar fase “concluída” sem evidência de validação compatível com o escopo da própria fase.

