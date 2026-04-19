# Plano Limpo (Pendências Finais)

Data: 2026-04-19

## Pendências em Execução

- [x] **Pendência 1 (Fase 2):** extração de estratégias concluída para `backend/src/domain/strategies`; pacote `backend/src/strategies` mantido somente como wrapper de compatibilidade.
- [x] **Pendência 2 (Fase 3):** fatiamento por camada concluído com módulo de dependências em `backend/src/interfaces/api/dependencies.py` e `api.py` reduzido a composição + wrappers finos.
- [x] **Pendência 3 (Fase 9):** cutover/aposentadoria do legado corrigido concluídos com remoção de `.planning` e `frontend-vue-backup`, ajuste de runbooks/scripts e manutenção apenas dos caminhos oficiais.

## Regra de Fechamento

Cada pendência só pode ser marcada como concluída após:

1. Mudança de código aplicada.
2. Validação em Docker sem regressão.
3. Atualização deste plano com status final.

## Evidência de Validação

1. Suíte Docker completa: `make test-docker` -> `147 passed`.
2. Stack operacional: `docker compose ps` com `backend` e `frontend` saudáveis.
3. Contratos críticos online:
   - `GET /api/system/health` (backend) -> `200`
   - `GET /api/system/health` (BFF) -> `200`
   - `POST /api/sandbox/run` (BFF) -> `200`
