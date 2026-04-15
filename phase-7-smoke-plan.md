# Fase 7B: Plano de Smoke Tests

## 1. Objetivo

Este documento define a malha minima de smoke tests da `Fase 7B` para interfaces e wiring critico, depois que a baseline funcional da `Fase 7A` estiver estabelecida.

## 2. Leitura Executiva

Smoke tests aqui nao existem para provar corretude profunda. Eles existem para responder rapido:

- a interface principal ainda sobe?
- o contrato principal ainda responde?
- o wiring central ainda aponta para o fluxo certo?
- alguma regressao obvia foi introduzida?

Premissa:

- este documento so entra na execucao depois de API, BFF, frontend e WebSockets terem contratos minimamente reconciliados;
- corretude profunda de dominio, aplicacao, fixtures e datasets pertence a `Fase 7A`.

## 3. Escopo de Smoke

Cobertura minima recomendada:

- API do backend;
- BFF/proxies do frontend;
- WebSockets centrais;
- eventualmente smoke de pagina/fluxo no frontend.

## 4. Smoke da API

Endpoints prioritarios:

- `GET /api/v1/system/health`
- `GET /api/v1/system/indicators`
- `GET /api/v1/system/logs`
- `POST /api/v1/model/train`
- `POST /api/v1/simulation/run`
- `GET /api/v1/simulation/status`
- `GET /api/v1/simulation/summary`

O que validar:

- status code;
- shape basico do payload;
- erro padrao quando aplicavel;
- ausencia de side effect em query;
- wiring com caso de uso correto.

## 5. Smoke do BFF

Rotas prioritarias:

- `/api/system/health`
- `/api/system/indicators`
- `/api/system/logs`
- `/api/sandbox/run`

O que validar:

- proxy atinge backend correto;
- erro do backend nao vira dado “normal” silencioso;
- `source_status` e degradacao sao preservados quando existirem;
- contratos legados de compatibilidade continuam operando durante a transicao.

## 6. Smoke de WebSocket

Streams prioritarios:

- `pulse`
- `ticker`
- opcionalmente `logs`

O que validar:

- conexao abre;
- evento inicial `meta` existe;
- `source_status` esta presente;
- stream identifica corretamente se esta `real`, `mock`, `derived`, `degraded` ou `disabled`;
- desconexao e erro nao ficam silenciosos.

## 7. Smoke de Frontend

Nao precisa começar pesado.

Direcao recomendada:

- validar apenas fluxos mais criticos e sensiveis:
  - dashboard abre
  - pulse abre
  - sandbox abre
  - login nao vende funcionalidade inexistente

O que validar:

- pagina renderiza;
- estados basicos aparecem;
- dependencia do contrato principal esta integra;
- mocks e placeholders sao identificaveis.

## 8. Estrategia de Execucao Futura

P0:

- smoke de API
- smoke de BFF
- smoke de WebSocket

P1:

- smoke de frontend em paginas criticas

P2:

- smoke e2e mais encorpado se o custo compensar

## 9. Falhas que o Smoke Precisa Capturar

- rota fora do ar;
- payload sem shape esperado;
- query disparando processamento pesado;
- BFF mascarando erro;
- stream sem metadata;
- UI “live” em cima de dado mockado sem indicacao.

## 10. O que Nao Esperar do Smoke

- nao mede corretude profunda do dominio;
- nao substitui integracao de repository;
- nao substitui cenarios de ouro de simulacao;
- nao substitui avaliacao do LLM.

## 11. Status do Entregavel

- status: `draft-initial`
- pronto para orientar a camada minima de validacao rapida da `Fase 7B`
- deve ser refinado quando a execucao das fases 5 e 6 comecar
