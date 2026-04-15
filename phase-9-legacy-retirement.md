# Fase 9: Aposentadoria do Legado

## 1. Objetivo

Este documento define o que do legado deve ser aposentado, em que ordem e sob quais criterios.

## 2. Leitura Executiva

O risco da Fase 9 nao e so cortar cedo demais. E tambem deixar restos de legado vivos por comodidade e reintroduzir o monolito por inercia.

## 3. Alvos Principais de Aposentadoria

## 3.1 Backend Monolitico

Itens prioritarios:

- `backend/src/api.py` como centro da regra
- `backend/src/system_runner.py` como orquestrador central
- `backend/src/main.py` como caminho all-in-one legado, se deixar de ter papel claro

Regra:

- podem continuar apenas se reduzidos a wrappers temporarios e com remocao planejada;
- nao devem permanecer como centro operacional.

## 3.2 Compatibilidades Temporarias

Itens prioritarios:

- aliases de `/api/*` para `/api/v1/*`
- adaptadores de payload legado
- aliases de WebSocket

Regra:

- remover por item, com criterio de remocao explicitado na Fase 5.

## 3.3 Frontend Legado

Item prioritario:

- `frontend-vue-backup/`

Direcao recomendada:

- tratar como legado arquivado;
- retirar da narrativa oficial do repo;
- decidir se sera removido, movido para arquivo historico ou documentado apenas como backup.

## 3.4 Documentacao Obsoleta

Itens observados:

- README principal ainda descreve estado antigo e promete rotas/arquitetura fora de sincronia;
- `AGENTS.md` do repo ainda fala em Vue 3 + Vite para o frontend principal;
- docs pontuais ainda apontam para `api.py` monolitico como centro oficial.

Regra:

- a documentacao antiga precisa ser tratada como legado e atualizada ou removida.

## 3.5 Scripts e Fluxos Antigos

Itens observados:

- `Makefile` ainda anuncia `run-frontend` como “Vue frontend locally with Vite”, embora o frontend oficial seja Next.js;
- scripts e comandos antigos nao podem continuar parecendo caminho oficial se nao forem mais a realidade;
- `setup_cloud.sh` precisa ser reavaliado contra a arquitetura final antes de permanecer como fluxo oficial.

## 4. Criterios de Remocao

Um item do legado so pode ser aposentado quando:

- existe substituto oficial claro;
- baseline relevante passou;
- consumidor conhecido migrou;
- rollback foi pensado;
- docs ja apontam para o substituto.

## 5. Ordem Recomendada de Aposentadoria

1. payloads e aliases claramente substituidos
2. wrappers temporarios sem consumidor ativo
3. modulos monoliticos reduzidos a ponte
4. restos de frontend e docs obsoletas
5. scripts e caminhos antigos de operacao

## 6. O que Nao Deve Ser Removido Cedo Demais

- compatibilidade ainda consumida pelo frontend oficial;
- caminhos de rollback da onda atual;
- docs que ainda servem como unica referencia operacional ate serem reescritas;
- evidencias historicas relevantes sem destino claro.

## 7. Status do Entregavel

- status: `draft-initial`
- pronto para orientar a remocao do legado na Fase 9
- deve ser refinado com a lista final de consumidores e pontos de entrada oficiais
