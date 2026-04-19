# Legacy Retirement Matrix (Fase 9)

Data de referência: 2026-04-19

Este documento transforma a aposentadoria do legado em itens verificáveis, com critério de remoção, evidência e estado atual.

## Escala de status

- `ACTIVE`: ainda faz parte do fluxo oficial.
- `TRANSITION`: em migração; remoção depende de gates.
- `RETIRED`: aposentado do fluxo oficial (pode permanecer como histórico).

## Matriz

| Item | Categoria | Status | Critério de remoção | Evidência atual | Próximo passo |
|---|---|---|---|---|---|
| `backend/src/api.py` como “centro monolítico” | Backend | TRANSITION | `api.py` virar apenas composição de routers e bootstrap | rotas WS, control-center e simulation-run já extraídas | continuar fatiamento de endpoints `/api/v1/*` restantes |
| `backend/src/system_runner.py` como orquestrador global único | Backend | TRANSITION | casos de uso/adapters cobrirem chamadas principais sem acoplamento direto | adapters + wrappers de compatibilidade implementados | reduzir chamadas diretas e concentrar em application layer |
| aliases e compatibilidade de payload temporária | API/BFF | TRANSITION | todos consumidores no contrato canônico | BFF crítico validado com `200` nas rotas centrais | mapear e remover aliases residuais por item |
| `frontend-vue-backup/` | Frontend | RETIRED | removido do repositório e fora do fluxo oficial | diretório removido; frontend oficial é Next.js (`frontend/`) | manter descontinuado |
| referências operacionais antigas em docs | Docs | TRANSITION | README/AGENTS/runbooks alinhados ao fluxo atual | runbook de cutover criado | varrer e corrigir referências divergentes remanescentes |
| fluxo sem rollback explícito | Operação | RETIRED | runbook com ondas + rollback publicado | `docs/CUTOVER_RUNBOOK.md` | manter atualizado conforme novos cortes |

## Gates para declarar encerramento da Fase 9

1. `api.py` reduzido a composição/bootstrapping.
2. nenhuma rota crítica depender de alias legado sem justificativa.
3. nenhum diretório legado de frontend paralelo ativo no repositório.
4. documentação principal sem conflito de stack/ponto de entrada.
5. regressão smoke e suíte focal passando no Docker.
