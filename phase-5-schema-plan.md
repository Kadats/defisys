# Fase 5: Plano de Schemas HTTP

## 1. Objetivo

Este documento define o plano de schemas HTTP da Fase 5.

A meta aqui e preparar contratos de request e response que:

- reflitam os casos de uso definidos na Fase 1;
- desacoplem a API do shape atual de tabela e payload improvisado;
- permitam compatibilidade controlada com o frontend atual;
- deixem claro quando a resposta e real, derivada, mockada ou degradada.

## 2. Principios dos Schemas

- schema HTTP nao replica tabela de banco;
- schema HTTP nao replica DTO interno cegamente;
- response de query deve ser estavel, previsivel e livre de side effect;
- command deve devolver aceite, status, ids e warnings, nao payload ambigo;
- erro deve ter shape padrao;
- degradacao e fallback devem ser explicitados no contrato;
- campos opcionais precisam ser justificados por transicao ou natureza do dado.

## 3. Modelo de Envelope Recomendado

Direcao recomendada:

- evitar envelope global obrigatorio para tudo se isso gerar ruido desnecessario;
- permitir response direta quando o recurso e simples;
- usar envelope padrao quando houver:
  - warnings
  - source status
  - metadados de pagina
  - compatibilidade de migracao

Shape conceitual sugerido para responses compostas:

```text
{
  data: ...,
  warnings: [...],
  meta: {
    request_id,
    schema_version,
    generated_at,
    source_status
  }
}
```

Onde:

- `warnings` e opcional;
- `meta` e obrigatorio apenas em respostas compostas ou operacionais;
- `source_status` deve indicar se o payload e:
  - `real`
  - `derived`
  - `mock`
  - `degraded`

## 4. Politica de Erros

Todos os endpoints novos devem convergir para um shape de erro padrao:

```text
{
  error: {
    code,
    message,
    category,
    retryable
  },
  meta: {
    request_id,
    schema_version,
    generated_at
  }
}
```

Campos recomendados:

- `code`
  - identificador tecnico curto
- `message`
  - mensagem legivel
- `category`
  - `validation`
  - `not_found`
  - `conflict`
  - `dependency`
  - `internal`
- `retryable`
  - boolean para orientar UI e automacao

## 5. Politica de Versionamento

- contratos novos nascem em `/api/v1/*`;
- `schema_version` deve existir em responses compostas e operacionais;
- alteracao breaking relevante exige:
  - rota nova
  - ou alias de compatibilidade temporario
- nao fazer mutacao silenciosa de payload em endpoint legado consumido pela UI.

## 6. Schemas Prioritarios por Router

## 6.1 System

### `GET /api/v1/system/health`

Tipo:

- query simples

Response alvo:

- `rpc_nodes`
- `overall_status`
- `checked_at`
- `warnings`

Observacoes:

- nao misturar health de RPC com health global da aplicacao sem deixar isso explicito;
- se houver degradacao parcial, isso deve aparecer como dado, nao so em log.

### `GET /api/v1/system/logs`

Tipo:

- query composta

Request sugerido:

- `limit`
- `cursor` ou `offset`
- `level`

Response alvo:

- `entries`
- `next_cursor`
- `meta`

Schema de item:

- `timestamp`
- `level`
- `message`
- `source`

Observacoes:

- evitar expor formato cru do arquivo de log;
- padronizar ordenacao e pagina.

### `GET /api/v1/system/indicators`

Tipo:

- query composta

Response alvo:

- `regime`
- `confidence`
- `btc_price`
- `market_bias`
- `health`
- `updated_at`
- `warnings`
- `meta.source_status`

Observacoes:

- hoje essa rota pode cair em fallback silencioso;
- na API nova, o contrato deve deixar claro se o valor veio de dado real ou payload degradado.

## 6.2 Market

### `GET /api/v1/market/chart-data`

Tipo:

- query

Request sugerido:

- `symbol`
- `timeframe`
- `start_date`
- `end_date`
- `limit`

Response alvo:

- `symbol`
- `timeframe`
- `candles`
- `meta`

Schema de candle:

- `open_time`
- `close_time`
- `open`
- `high`
- `low`
- `close`
- `volume`

Observacoes:

- este endpoint deve refletir `MarketCandle`, nao nomes fisicos de coluna.

### `GET /api/v1/market/analysis`

Tipo:

- query analitica

Request sugerido:

- `symbol`
- `timeframe`
- `window`

Response alvo:

- `analysis_period`
- `trend_summary`
- `volatility_summary`
- `market_regime_history`
- `meta`

Observacoes:

- separar resumo analitico de dados base para grafico.

## 6.3 Model

### `POST /api/v1/model/train`

Tipo:

- command

Request alvo:

- `dataset_ref`
- `train_split_date`
- `model_name`
- `model_version`
- `hyperparameters`

Response alvo:

- `accepted`
- `training_run_id`
- `status`
- `started_at`
- `warnings`
- `meta`

Observacoes:

- command nao deve devolver metrica final se o treino for assicrono;
- quando o resultado nao for imediato, responder com aceite e identificador de run.

## 6.4 Simulation

### `POST /api/v1/simulation/run`

Tipo:

- command

Request alvo:

- `strategy_name`
- `prediction_source_ref`
- `dataset_ref`
- `initial_capital_usd`
- `start_date`
- `end_date`
- `backtest_days`
- `enable_llm`
- `environment`

Response alvo:

- `accepted`
- `run_id`
- `status`
- `started_at`
- `warnings`
- `meta`

Observacoes:

- o contrato precisa distinguir claramente:
  - request aceito
  - job em progresso
  - job concluido
  - job falho

### `GET /api/v1/simulation/status`

Tipo:

- query

Response alvo:

- `run_id`
- `status`
- `started_at`
- `finished_at`
- `progress_pct`
- `has_summary`
- `warnings`
- `meta`

### `GET /api/v1/simulation/summary`

Tipo:

- query

Response alvo:

- `simulation_summary`
- `meta`

Conteudo esperado de `simulation_summary`:

- `run_id`
- `period`
- `initial_capital_usd`
- `final_equity_usd`
- `return_pct`
- `max_drawdown_pct`
- `trade_count`
- `treasury_breakdown`
- `llm_enabled`

Observacoes:

- este endpoint deve virar a fonte oficial de resumo, substituindo `/api/v1/summary`.

### `GET /api/v1/simulation/report`

Tipo:

- query composta

Response alvo:

- `summary`
- `trades`
- `positions`
- `kpis`
- `meta`

Observacoes:

- esse payload e para interface rica;
- nao deve substituir o summary oficial enxuto.

### `GET /api/v1/simulation/trades`

Tipo:

- query

Request sugerido:

- `run_id`
- `limit`
- `cursor`

Response alvo:

- `items`
- `next_cursor`
- `meta`

Schema de item:

- `trade_id`
- `timestamp`
- `action`
- `price`
- `quantity`
- `notional_usd`
- `reason`

### `GET /api/v1/simulation/positions`

Tipo:

- query

Response alvo:

- `open_positions`
- `closed_positions`
- `meta`

Schema de item:

- `position_id`
- `position_type`
- `status`
- `opened_at`
- `closed_at`
- `entry_price`
- `exit_price`
- `realized_pnl_usd`
- `unrealized_pnl_usd`

### `GET /api/v1/simulation/period`

Tipo:

- query

Response alvo:

- `run_id`
- `start_date`
- `end_date`
- `backtest_days`
- `meta`

## 6.5 Control Center

Schemas ainda dependem de detalhamento maior dos casos de uso agregados.

Direcao recomendada:

- preferir snapshots compostos e pequenos;
- evitar endpoint que mistura log, health, simulation e market num payload monolitico;
- qualquer snapshot deve informar `generated_at` e `source_status`.

## 6.6 Sandbox / Laboratorio

Se o endpoint de sandbox permanecer:

- o schema deve afirmar explicitamente que e laboratorio;
- o payload deve informar `source_status = mock`;
- o endpoint nao deve reaproveitar nome de recurso produtivo.

## 7. Mapeamento de Schemas Legados para Novos

Principais substituicoes planejadas:

- `/api/v1/summary`
  - substituido por `/api/v1/simulation/summary`
- `/api/v1/trade_history`
  - substituido por `/api/v1/simulation/trades`
- `/api/v1/backtest_period`
  - substituido por `/api/v1/simulation/period`
- `/api/history`
  - alias temporario ou aposentadoria em favor de `/api/v1/market/chart-data`

## 8. Campos que Precisam Ficar Explicitos na Migracao

Campos ou metadados que a API nova precisa tornar visiveis:

- `request_id`
- `schema_version`
- `generated_at`
- `source_status`
- `warnings`

Motivo:

- hoje a UI e os proxies escondem quando estao consumindo fallback, cache ou mock;
- a nova API precisa tornar isso auditavel.

## 9. Prioridade de Implementacao Futura

Prioridade P0:

- `system/health`
- `system/indicators`
- `simulation/status`
- `simulation/summary`
- `model/train`
- `simulation/run`

Prioridade P1:

- `system/logs`
- `market/chart-data`
- `simulation/trades`
- `simulation/positions`

Prioridade P2:

- `market/analysis`
- `control_center/*`
- `sandbox/*`

## 10. Dependencias para os Proximos Artefatos

Este plano deve alimentar:

- `phase-5-websocket-plan.md`
- `phase-5-compatibility-plan.md`

## 11. Status do Entregavel

- status: `draft-initial`
- pronto para orientar o desenho dos contratos HTTP da Fase 5
- ainda pode ser refinado quando a Fase 3 detalhar melhor os DTOs de aplicacao
