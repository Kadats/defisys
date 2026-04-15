# Fase 5: Route Map da Nova API

## 1. Objetivo

Este documento detalha o mapa de migracao das rotas HTTP da Fase 5.

A finalidade aqui nao e implementar a nova API ainda. E definir:

- como a superficie atual sera reorganizada;
- quais routers vao existir;
- quais rotas sao queries puras;
- quais rotas sao commands operacionais;
- quais endpoints legados precisam de compatibilidade temporaria;
- quais endpoints devem morrer.

## 2. Principios do Mapa

- uma rota deve chamar um caso de uso explicito;
- `GET` nao deve disparar processamento pesado;
- command e query devem ficar separados;
- a camada web nao acessa banco diretamente;
- nomes de rota devem refletir dominio funcional, nao detalhe interno;
- compatibilidade e temporaria e precisa de dono claro.

## 3. Estrutura-Alvo de Routers

Routers previstos para a nova API:

- `system`
- `market`
- `model`
- `simulation`
- `control_center`
- `paper_trading`

Bootstrap esperado:

- `api.py` ou `interfaces/api/app.py` apenas registra routers, middlewares, startup controlado e dependencies globais.

## 4. Politica de Namespace

Direcao recomendada:

- convergir a API HTTP para namespace versionado unico;
- adotar ` /api/v1/... ` como forma canonica dos contratos novos;
- manter aliases legados apenas quando houver consumidor real e prazo definido de remocao.

Decisao arquitetural recomendada:

- rotas novas nascem apenas em `/api/v1/*`;
- rotas antigas em `/api/*` ficam como compatibilidade temporaria ou sao aposentadas;
- nenhum contrato novo deve nascer fora do namespace versionado.

## 5. Mapa de Rotas Atuais para Routers Alvo

## 5.1 System

### `GET /api/system/health`

- classificacao atual: query
- router alvo: `system`
- rota canonica sugerida: `GET /api/v1/system/health`
- destino esperado: query de health snapshot
- status na migracao:
  - manter compatibilidade temporaria
- observacao:
  - bom candidato a migracao precoce por baixo risco.

### `GET /api/system/logs`

- classificacao atual: query
- router alvo: `system`
- rota canonica sugerida: `GET /api/v1/system/logs`
- destino esperado: query de log tail
- status na migracao:
  - manter compatibilidade temporaria
- observacao:
  - precisa ter contrato claro de pagina, limite e erro.

### `GET /api/system/indicators`

- classificacao atual: query
- router alvo: `system`
- rota canonica sugerida: `GET /api/v1/system/indicators`
- destino esperado: query de indicators snapshot
- status na migracao:
  - manter compatibilidade temporaria
- observacao:
  - payload hoje mistura dado real e fallback; isso precisa ser explicitado depois.

### `POST /api/sandbox/run`

- classificacao atual: command de laboratorio
- router alvo: `control_center` ou `paper_trading`
- rota canonica sugerida:
  - `POST /api/v1/control-center/sandbox/run`
- status na migracao:
  - manter temporariamente se a UI ainda consumir
- observacao:
  - nao deve parecer endpoint produtivo se o comportamento continuar fake.

## 5.2 Market

### `GET /api/history`

- classificacao atual: query
- router alvo: `market`
- rota canonica sugerida:
  - preferencialmente aposentar
  - ou manter como alias de `GET /api/v1/market/history`
- status na migracao:
  - legado forte
- observacao:
  - hoje esta acoplada a tabela fisica; nao deve ser modelo para a API nova.

### `GET /api/v1/chart_data`

- classificacao atual: query
- router alvo: `market`
- rota canonica sugerida: `GET /api/v1/market/chart-data`
- destino esperado: query de candles para chart
- status na migracao:
  - manter e normalizar
- observacao:
  - parece ser a rota mais proxima do frontend real e deve virar referencia.

### `GET /api/v1/market_analysis`

- classificacao atual: query analitica
- router alvo: `market` ou `control_center`
- rota canonica sugerida: `GET /api/v1/market/analysis`
- status na migracao:
  - manter com revisao de payload
- observacao:
  - separar claramente analise historica de runtime operacional.

## 5.3 Model

### `POST /api/model/train`

- classificacao atual: command
- router alvo: `model`
- rota canonica sugerida: `POST /api/v1/model/train`
- destino esperado: command `train_model`
- status na migracao:
  - migracao obrigatoria
- observacao:
  - precisa de contrato de job e resposta padronizada.

## 5.4 Simulation

### `GET /api/simulation`

- classificacao atual: query composta
- router alvo: `simulation`
- rota canonica sugerida:
  - `GET /api/v1/simulation/report`
- destino esperado: query de simulation report
- status na migracao:
  - manter temporariamente enquanto frontend migrar
- observacao:
  - payload deve ser separado entre report detalhado e summary oficial.

### `POST /api/simulation/run`

- classificacao atual: command
- router alvo: `simulation`
- rota canonica sugerida: `POST /api/v1/simulation/run`
- destino esperado: command `run_backtest`
- status na migracao:
  - manter e formalizar
- observacao:
  - deve retornar contrato de job/status, nao apenas side effect solto.

### `GET /api/simulation/status`

- classificacao atual: query
- router alvo: `simulation`
- rota canonica sugerida: `GET /api/v1/simulation/status`
- destino esperado: query de status
- status na migracao:
  - manter e formalizar

### `GET /api/simulation/summary`

- classificacao atual: query
- router alvo: `simulation`
- rota canonica sugerida: `GET /api/v1/simulation/summary`
- destino esperado: query de summary oficial
- status na migracao:
  - manter e formalizar

### `GET /api/v1/summary`

- classificacao atual: query com side effect potencial
- router alvo: `simulation`
- rota canonica sugerida:
  - aposentar em favor de `GET /api/v1/simulation/summary`
- status na migracao:
  - deprecate
- observacao:
  - nao pode continuar disparando execucao implicita.

### `GET /api/v1/trade_history`

- classificacao atual: query com side effect potencial
- router alvo: `simulation`
- rota canonica sugerida: `GET /api/v1/simulation/trades`
- status na migracao:
  - manter via alias temporario
- observacao:
  - precisa virar query pura.

### `GET /api/v1/backtest_period`

- classificacao atual: query com side effect potencial
- router alvo: `simulation`
- rota canonica sugerida: `GET /api/v1/simulation/period`
- status na migracao:
  - manter via alias temporario
- observacao:
  - precisa parar de depender de execucao indireta.

### `GET /api/v1/positions`

- classificacao atual: query
- router alvo: `simulation`
- rota canonica sugerida: `GET /api/v1/simulation/positions`
- status na migracao:
  - manter e formalizar
- observacao:
  - bom candidato a query oficial desde cedo.

## 5.5 Control Center

Rotas do painel operacional que nao sao estritamente market, model ou simulation devem convergir para `control_center`.

Alvos mais provaveis:

- snapshots agregados para dashboard;
- estado do system pulse;
- status operacional consolidado;
- operacoes de laboratorio que nao sejam paper trading formal.

Observacao:

- nesta etapa ainda nao ha rota canonica fechada para `control_center`;
- isso depende do mapa de queries da Fase 3.

## 5.6 Paper Trading

Nao ha superficie madura claramente identificada ainda.

Direcao recomendada:

- reservar router proprio para quando paper trading deixar de ser apenas derivacao do backtest;
- nao misturar paper trading futuro com `sandbox` fake atual.

## 6. Rotas que Devem Morrer

Rotas com maior prioridade de aposentadoria:

- `GET /api/v1/summary`
- `GET /api/v1/trade_history`
- `GET /api/v1/backtest_period`
- `GET /api/history`

Motivos:

- namespace inconsistente;
- side effect em query;
- acoplamento forte ao legado;
- sobreposicao com contratos mais claros possiveis na nova API.

## 7. Rotas que Devem Ser Primeiras na Migracao

Prioridade P0:

- `GET /api/system/health`
- `GET /api/system/indicators`
- `GET /api/simulation/status`
- `GET /api/simulation/summary`
- `POST /api/model/train`
- `POST /api/simulation/run`

Prioridade P1:

- `GET /api/system/logs`
- `GET /api/v1/chart_data`
- `GET /api/v1/positions`
- `GET /api/simulation`

Prioridade P2:

- `GET /api/v1/market_analysis`
- `POST /api/sandbox/run`
- aliases legados restantes

## 8. Regras de Compatibilidade

- alias legado deve apontar para o novo caso de uso, nunca manter implementacao paralela indefinida;
- cada alias deve ter dono e criterio de remocao;
- payloads antigos so devem ser preservados onde houver consumidor mapeado;
- quando um endpoint mudar semanticamente, isso deve acontecer em rota nova, nao em mutacao silenciosa do legado.

## 9. Dependencias para os Proximos Artefatos

Este mapa deve alimentar:

- `phase-5-schema-plan.md`
- `phase-5-websocket-plan.md`
- `phase-5-compatibility-plan.md`

## 10. Status do Entregavel

- status: `draft-initial`
- pronto para servir de baseline da modularizacao de rotas da Fase 5
- ainda pode ser refinado quando o mapa de casos de uso da Fase 3 estiver mais detalhado
