# DefiSys Cutover Runbook (Fase 9)

Este runbook define um cutover incremental com rollback rápido para o stack Docker do projeto.

## Objetivo

- consolidar backend + frontend nos contratos canônicos atuais;
- validar comportamento operacional mínimo antes de declarar fechamento de migração;
- garantir rollback objetivo por onda.

## Pré-condições

- imagens atualizadas via Docker:
  - `docker compose build backend frontend backend-test`
- banco de teste saudável:
  - `docker compose ps`
- smoke suite verde:
  - `make test-smoke-docker`

## Onda 0: Baseline

1. Subir stack:
   - `docker compose up -d postgres postgres_paper postgres_test backend frontend`
2. Verificar saúde:
   - `docker compose ps`
3. Verificar contratos críticos backend:
   - `curl -sS http://127.0.0.1:8000/api/system/health`
   - `curl -sS http://127.0.0.1:8000/api/system/indicators`

Rollback:
- `docker compose down`
- voltar para commit/tag anterior e repetir `docker compose up -d`.

## Onda 1: BFF Canonical

1. Validar proxies críticos via frontend:
   - `curl -sS -o /tmp/cc_health.json -w "%{http_code}\n" http://127.0.0.1:3000/api/system/health`
   - `curl -sS -o /tmp/cc_indicators.json -w "%{http_code}\n" http://127.0.0.1:3000/api/system/indicators`
   - `curl -sS -o /tmp/cc_logs.json -w "%{http_code}\n" http://127.0.0.1:3000/api/system/logs`
   - `curl -sS -o /tmp/cc_sandbox.json -w "%{http_code}\n" -X POST -H "Content-Type: application/json" -d '{"ai_confidence":0.8,"initial_capital":5000,"train_window":90,"test_window":30}' http://127.0.0.1:3000/api/sandbox/run`
2. Critério:
   - todas as rotas acima com `200`.

Rollback:
- se qualquer rota retornar `503`, investigar `backend` e `frontend` logs:
  - `docker compose logs --tail=200 backend`
  - `docker compose logs --tail=200 frontend`
- reverter o último commit de frontend/BFF e repetir onda.

## Onda 2: Runtime Paper

1. Validar smoke runtime paper:
   - `docker compose --profile test run --rm -e PYTHONPATH=/app backend-test pytest -q tests/smoke/test_paper_runtime_smoke.py`
2. Critério:
   - fluxo normal, kill-switch, health-factor crítico e feed degradado passando.

Rollback:
- se falhar, reverter última alteração em `backend/src/services/paper_runtime.py` e `backend/src/interfaces/api/paper_runtime_routes.py`.

## Onda 3: Gate Final

1. Executar gate smoke completo:
   - `make test-smoke-docker`
2. Executar regressão focada:
   - `docker compose --profile test run --rm -e PYTHONPATH=/app backend-test pytest -q tests/test_api.py tests/test_control_center_api.py tests/test_application_use_cases.py`
3. Registrar evidências:
   - comandos executados;
   - status por suíte;
   - hash de commit liberado.

Rollback:
- `docker compose down`
- `git checkout <tag-ou-commit-estavel>`
- `docker compose up -d`

## Critério de Encerramento da Migração Parcial

- Fases 4-8 com evidência técnica registrada;
- BFF canônico sem fallback indevido no cenário saudável;
- runtime paper com smoke de risco/degradação;
- `plan.md` limpo e coerente com evidência técnica executada.
