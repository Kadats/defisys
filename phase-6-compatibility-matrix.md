# Fase 6: Matriz de Compatibilidade do Frontend

## 1. Objetivo

Este documento cruza consumidores do frontend com contratos HTTP e WebSocket para orientar a reconciliacao da Fase 6.

## 2. Matriz por Consumidor

## 2.1 `frontend/src/components/TickerHeader.tsx`

Consome:

- `WS /api/ws/ticker`
- `GET /api/system/health`

Problemas atuais:

- ticker pode ser mockado;
- BTC tem fallback local;
- ETH e sintetizado no cliente;
- health usa proxy com payload offline inventado.

Contrato alvo:

- `WS /api/v1/ws/market/ticker`
- `GET /api/v1/system/health`

Tipo de compatibilidade esperado:

- alias de rota para health
- compatibilidade de WebSocket para ticker
- politica de estado de UI obrigatoria

Observacao:

- este e o ponto mais critico de ambiguidade semantica do frontend atual.

## 2.2 `frontend/src/components/IndicatorWidget.tsx`

Consome:

- `GET /api/system/indicators`

Problemas atuais:

- defaults locais mascaram falha;
- regime default pode parecer leitura real.

Contrato alvo:

- `GET /api/v1/system/indicators`

Tipo de compatibilidade esperado:

- alias de rota
- adaptador de payload curto

## 2.3 `frontend/src/app/dashboard/page.tsx`

Consome:

- `WS /api/ws/ticker`
- `IndicatorWidget`

Problemas atuais:

- usa status do ticker como sinal geral de sistema online/offline;
- carrega placeholders visuais fortes;
- label “LIVE FEED” hoje nao e confiavel em todos os cenarios.

Contrato alvo:

- `WS /api/v1/ws/market/ticker`
- contratos novos de indicadores

Tipo de compatibilidade esperado:

- compatibilidade de WebSocket
- revisao de copy

## 2.4 `frontend/src/app/dashboard/pulse/page.tsx`

Consome:

- `WS /api/ws/pulse`
- `GET /api/system/logs`

Problemas atuais:

- stream sem metadata operacional;
- logs por BFF ainda misturam erro e dado.

Contrato alvo:

- `WS /api/v1/ws/system/pulse`
- `GET /api/v1/system/logs`

Tipo de compatibilidade esperado:

- alias de stream
- alias de rota

## 2.5 `frontend/src/app/dashboard/sandbox/page.tsx`

Consome:

- `POST /api/sandbox/run`

Problemas atuais:

- fluxo laboratorial pode parecer mais produtivo do que realmente e;
- semantica do modulo depende do backend fake atual.

Contrato alvo:

- `POST /api/v1/control-center/sandbox/run`

Tipo de compatibilidade esperado:

- alias de rota
- copy explicita de laboratorio

## 2.6 `frontend/src/app/login/page.tsx`

Consome:

- nenhum backend real identificado

Problema atual:

- placeholder puro

Contrato alvo:

- a definir apenas quando houver fluxo real

Tipo de compatibilidade esperado:

- nenhum

Observacao:

- tratar como fluxo ausente, nao como contrato em migracao.

## 3. Matriz por Contrato

## 3.1 HTTP

### `GET /api/system/health`

Consumidores:

- `TickerHeader`

Substituto:

- `GET /api/v1/system/health`

Compatibilidade:

- obrigatoria na transicao

### `GET /api/system/indicators`

Consumidores:

- `IndicatorWidget`

Substituto:

- `GET /api/v1/system/indicators`

Compatibilidade:

- obrigatoria na transicao

### `GET /api/system/logs`

Consumidores:

- `SystemPulsePage`

Substituto:

- `GET /api/v1/system/logs`

Compatibilidade:

- obrigatoria na transicao

### `POST /api/sandbox/run`

Consumidores:

- `SandboxLabPage`

Substituto:

- `POST /api/v1/control-center/sandbox/run`

Compatibilidade:

- curta, com semantica de laboratorio explicita

## 3.2 WebSocket

### `WS /api/ws/ticker`

Consumidores:

- `TickerHeader`
- `DashboardPage`

Substituto:

- `WS /api/v1/ws/market/ticker`

Compatibilidade:

- critica

Risco:

- manter mock oculto sob aparencia de feed real

### `WS /api/ws/pulse`

Consumidores:

- `SystemPulsePage`

Substituto:

- `WS /api/v1/ws/system/pulse`

Compatibilidade:

- obrigatoria na transicao

## 4. Prioridade de Reconciliacao

P0:

- `TickerHeader`
- `IndicatorWidget`
- `SystemPulsePage`

P1:

- `DashboardPage`
- `SandboxLabPage`

P2:

- `LoginPage`
- limpeza de restos de stack e documentacao

## 5. Criterios de Remocao de Compatibilidade no Frontend

Podemos retirar compatibilidade quando:

- o componente consumidor ja estiver apontando para o contrato canonico;
- a UI souber representar `source_status` corretamente;
- fallback enganoso tiver sido removido;
- a copy da pagina nao vender estado melhor do que o sistema entrega;
- a documentacao da tela estiver alinhada.

## 6. Status do Entregavel

- status: `draft-initial`
- pronto para guiar a reconciliacao concreta do frontend na Fase 6
- deve ser refinado junto da execucao da Fase 5 e da futura execucao da Fase 6
