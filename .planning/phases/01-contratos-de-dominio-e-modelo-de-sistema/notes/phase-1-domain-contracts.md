# Fase 1: Contratos de Dominio

## 1. Objetivo

Definir os contratos centrais do dominio para que a Fase 2 possa extrair codigo puro sem herdar a ambiguidade estrutural do legado.

## 2. Leitura Executiva

Os contratos abaixo nao descrevem tabela, rota HTTP nem DataFrame especifico. Eles descrevem os objetos que o sistema precisa entender para continuar fazendo o mesmo trabalho com arquitetura melhor.

Diretriz:

- entidade quando houver identidade e ciclo de vida;
- value object quando houver composicao imutavel sem identidade de negocio;
- contrato separado para resultado analitico e resumo oficial persistido.

## 3. Contratos Canonicos

## 3.1 `MarketCandle`

Tipo sugerido:

- value object

Campos minimos:

- `symbol`
- `timeframe`
- `open_time`
- `close_time`
- `open`
- `high`
- `low`
- `close`
- `volume`

Invariantes:

- `open_time < close_time`
- `high >= max(open, close, low)`
- `low <= min(open, close, high)`
- valores numericos nao negativos
- representa candle fechado, nao candle em formacao

Observacoes de migracao:

- nasce do legado `btcusdt_4h_klines`;
- deve deixar de depender de nomes como `Open_time` e `Close`.

## 3.2 `FeatureVector`

Tipo sugerido:

- value object

Campos minimos:

- `symbol`
- `timeframe`
- `as_of_time`
- `market_candle_ref`
- `features`

Campos conceituais esperados em `features`:

- momentum
- trend
- volatility
- sentiment
- derivatives
- defi

Invariantes:

- `as_of_time` deve refletir somente informacao disponivel ate o momento da decisao
- nao pode conter target
- nao pode conter leakage de futuro
- precisa ser rastreavel ate o candle base

Observacoes de migracao:

- no legado, isso esta diluido em `full_df` e `prepared data`.

## 3.3 `Prediction`

Tipo sugerido:

- value object

Campos minimos:

- `as_of_time`
- `symbol`
- `timeframe`
- `label`
- `confidence`
- `model_name`
- `model_version`
- `horizon`

Campos opcionais:

- `prediction_correct`
- `threshold_used`
- `features_version`
- `run_id`

Invariantes:

- `confidence` entre `0.0` e `1.0`
- previsao e confianca pertencem ao mesmo instante observavel
- `Prediction` nao decide execucao sozinha

Observacoes de migracao:

- unifica `prediction`, `prediction_proba` e metadados que hoje estao dispersos.

## 3.4 `PortfolioState`

Tipo sugerido:

- entidade agregada ou snapshot rico, sem necessidade de persistencia identica ao banco

Campos minimos:

- `timestamp`
- `cash_usd`
- `btc_spot`
- `lp_positions_value_usd`
- `lp_fees_usd`
- `aave_collateral_usd`
- `aave_debt_usd`
- `health_factor`
- `total_equity_usd`

Campos opcionais:

- `reserved_gas_usd`
- `net_btc_exposure`
- `active_positions_count`

Invariantes:

- `cash_usd >= 0`
- `aave_collateral_usd >= 0`
- `aave_debt_usd >= 0`
- `health_factor` precisa ser calculavel quando houver divida
- `total_equity_usd` precisa ser coerente com os blocos da carteira

Observacoes de migracao:

- consolida a visao hoje espalhada entre engine, summary e payload de dashboard.

## 3.5 `Position`

Tipo sugerido:

- entidade

Campos minimos:

- `position_id`
- `position_type`
- `status`
- `opened_at`
- `closed_at`
- `entry_price`
- `exit_price`
- `capital_allocated_usd`
- `realized_pnl_usd`
- `unrealized_pnl_usd`

Campos conceituais adicionais por tipo:

- LP:
  - `range_lower`
  - `range_upper`
- leverage:
  - `collateral_usd`
  - `debt_usd`

Invariantes:

- `position_id` unico
- `opened_at` obrigatorio
- `closed_at` so existe para posicao encerrada
- `status` e `closed_at` devem ser coerentes

Observacoes de migracao:

- hoje o legado mistura `positions_log`, `active_lps` e partes do engine.

## 3.6 `TradeRecord`

Tipo sugerido:

- entidade de evento ou value object identificavel

Campos minimos:

- `trade_id`
- `timestamp`
- `action`
- `quantity`
- `price`
- `notional_usd`
- `post_trade_equity_usd`
- `position_ref`
- `reason`

Invariantes:

- `timestamp` obrigatorio
- `action` deve estar em conjunto finito conhecido
- `post_trade_equity_usd` nao pode ser indefinido no contrato final

Observacoes de migracao:

- corrige a mistura atual entre trilha de evento e payload de apresentacao.

## 3.7 `RiskSnapshot`

Tipo sugerido:

- value object

Campos minimos:

- `timestamp`
- `health_factor`
- `health_status`
- `global_drawdown_pct`
- `daily_drawdown_pct`
- `gas_reserve_usd`
- `can_open_new_risk`
- `kill_switch_active`

Campos opcionais:

- `warnings`
- `liquidation_distance`
- `leverage_allowed`

Invariantes:

- kill switch tem precedencia sobre qualquer sinal
- health factor precisa refletir o estado atual da carteira
- `can_open_new_risk` deve ser falso quando limites criticos forem violados

Observacoes de migracao:

- deriva de `RiskManager` e dos thresholds de config, mas vira contrato explicito.

## 3.8 `LLMDecision`

Tipo sugerido:

- value object de integracao normalizada

Campos minimos:

- `action`
- `amount_pct`
- `reason`
- `provider`
- `model`
- `source`

Campos opcionais:

- `raw_response_ref`
- `latency_ms`
- `validation_flags`

Invariantes:

- `action` deve pertencer ao conjunto permitido
- `amount_pct` entre `0.0` e `1.0`
- `reason` obrigatorio e curto
- `source` deve distinguir `llm` de `fallback`

Observacoes de migracao:

- a resposta bruta do Gemini nao deve circular acima deste formato.

## 3.9 `StrategyDecision`

Tipo sugerido:

- value object

Campos minimos:

- `action`
- `amount_pct`
- `reason`
- `decision_source`
- `prediction_ref`
- `regime`
- `risk_snapshot_ref`

Campos opcionais:

- `llm_decision_ref`
- `priority`
- `execution_hints`

Invariantes:

- `action` deve pertencer ao conjunto permitido pelo dominio
- `amount_pct` entre `0.0` e `1.0`
- se `kill_switch_active`, a decisao nao pode abrir risco novo
- decisao final precisa ser rastreavel aos insumos que a produziram

Observacoes de migracao:

- este e o contrato que a estrategia entrega ao motor;
- ele separa claramente sinal de execucao.

## 3.10 `BacktestResult`

Tipo sugerido:

- value object rico de resultado analitico

Campos minimos:

- `run_id`
- `strategy_name`
- `start_date`
- `end_date`
- `initial_capital_usd`
- `final_equity_usd`
- `roi_pct`
- `benchmark_roi_pct`
- `token_roi_pct`
- `alpha_vs_hold_pct`
- `max_drawdown_pct`
- `sharpe_ratio`
- `total_trades`

Campos opcionais:

- `win_rate`
- `prediction_stats`
- `equity_curve_ref`
- `notes`

Invariantes:

- `start_date <= end_date`
- `total_trades >= 0`
- metricas devem se referir ao mesmo `run_id`

Observacoes de migracao:

- corresponde ao `backtest_report` do legado, mas em formato mais estavel.

## 3.11 `SimulationSummary`

Tipo sugerido:

- value object persistivel e oficial

Campos minimos:

- `run_id`
- `timestamp`
- `initial_capital_usd`
- `total_equity_usd`
- `roi_pct`
- `benchmark_roi_pct`
- `cash_usd`
- `btc_amount`
- `btc_price_final`
- `wallet_spot_total_usd`
- `wallet_lp_value_usd`
- `lp_active_count`
- `lp_fees_usd`
- `aave_collateral_usd`
- `aave_debt_usd`
- `aave_health_factor`
- `initial_token_balance`
- `final_token_balance`
- `token_roi_pct`
- `alpha_vs_hold_pct`
- `total_trades`

Invariantes:

- deve ser suficiente para alimentar queries oficiais sem recalculo pesado
- precisa preservar separacao conceitual das tesourarias
- um `run_id` identifica uma simulacao oficial

Observacoes de migracao:

- corresponde ao `simulation_summary` do banco;
- e fonte de verdade para UI e consultas de status.

## 4. Conjuntos Finitos Recomendados

## 4.1 `StrategyAction`

Conjunto inicial recomendado:

- `DEFENSE_MODE`
- `BORROW_AND_LP`
- `CONSERVATIVE_LP`
- `SPOT_ONLY`
- `DO_NOTHING`
- `TAKE_PROFIT`
- `STOP_LOSS`
- `DIRECTIONAL_SHORT`
- `CLOSE_POSITION`

Observacao:

- o subset efetivo pode variar por estrategia;
- o contrato precisa manter enum conhecido e validavel.

## 4.2 `PositionStatus`

- `OPEN`
- `CLOSED`
- `LIQUIDATED`
- `CANCELLED`

## 4.3 `DecisionSource`

- `heuristic`
- `llm`
- `policy`
- `hybrid`
- `system_guardrail`

## 5. Invariantes Cruzadas

- `MarketCandle` -> `FeatureVector` -> `Prediction` -> `StrategyDecision` deve manter causalidade temporal.
- `RiskSnapshot` deve ter precedencia sobre `Prediction` quando houver conflito de seguranca.
- `LLMDecision` nunca pula direto para execucao; ela sempre vira `StrategyDecision` validada.
- `BacktestResult` e `SimulationSummary` compartilham o mesmo `run_id`, mas nao o mesmo papel.
- `DashboardSnapshot` fica fora do dominio puro e deve ser derivado a partir de `SimulationSummary` e consultas auxiliares.

## 6. Mapeamento Inicial com o Legado

- `btcusdt_4h_klines` -> `MarketCandle`
- `prepared data` / `full_df` -> `FeatureVector`
- `ml_predictions` -> `Prediction`
- `RiskManager` outputs -> `RiskSnapshot`
- `transaction_log` / tabela `trades` -> `TradeRecord`
- `positions_log` -> `Position`
- `backtest_report` -> `BacktestResult`
- `simulation_summary` -> `SimulationSummary`

## 7. Conclusao

Esses contratos definem o nucleo sem obrigar a reescrita inteira agora.

Leitura pratica:

- o dominio novo passa a falar por objetos claros;
- o legado vira fonte de mapeamento;
- a Fase 2 pode comecar pela extracao de risco, portfolio e decisao sem redesenhar tudo ao mesmo tempo.

