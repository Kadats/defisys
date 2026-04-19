# Fase 1: Casos de Uso

## 1. Objetivo

Definir os casos de uso centrais da aplicacao com contratos claros de entrada e saida, desacoplando-os da forma atual de `api.py`, `system_runner.py` e `pipeline.py`.

## 2. Leitura Executiva

O sistema atual tem poucos fluxos reais, mas eles aparecem embaralhados em funcoes monoliticas. A meta aqui e transformar esses fluxos em casos de uso explicitos.

Diretriz:

- comando muda estado ou produz artefato operacional;
- consulta le estado consolidado sem disparar execucao pesada;
- DTO de entrada/saida nao herda shape de tabela nem payload de tela.

## 3. Casos de Uso Canonicos

## 3.1 `sync_market_data`

Tipo:

- command

Finalidade:

- sincronizar candles e fontes auxiliares no banco operacional.

Input sugerido:

- `symbol`
- `timeframe`
- `force_full_sync`
- `sources_enabled`
- `trigger_source`

Output sugerido:

- `run_id`
- `started_at`
- `finished_at`
- `sources_synced`
- `rows_written_by_source`
- `warnings`
- `success`

Dependencias abstratas:

- market data gateways
- repositories de persistencia
- logger

Mapeamento legado:

- `backend/src/data/pipeline.py::sync_market_data`
- startup em `backend/src/api.py`

## 3.2 `prepare_features`

Tipo:

- command tecnico ou job interno

Finalidade:

- transformar `MarketCandle` e fontes auxiliares em `FeatureVector` rastreavel e causal.

Input sugerido:

- `symbol`
- `timeframe`
- `start_date`
- `end_date`
- `feature_set_version`
- `rebuild_mode`

Output sugerido:

- `dataset_ref`
- `feature_count`
- `row_count`
- `time_window`
- `warnings`

Dependencias abstratas:

- repositories de market data
- feature builders
- validadores de causalidade

Mapeamento legado:

- parte de `backend/src/data/pipeline.py::get_full_prepared_data`

## 3.3 `train_model`

Tipo:

- command

Finalidade:

- treinar o modelo quantitativo com split temporal e registrar metadados do treinamento.

Input sugerido:

- `dataset_ref`
- `train_split_date`
- `model_name`
- `model_version`
- `hyperparameters`

Output sugerido:

- `training_run_id`
- `model_ref`
- `train_window`
- `validation_metrics`
- `success`
- `warnings`

Dependencias abstratas:

- dataset provider
- model trainer
- artifact registry ou metadata store

Mapeamento legado:

- `backend/src/system_runner.py::train_model_pipeline`
- parte de `run_trading_system`

## 3.4 `generate_predictions`

Tipo:

- command

Finalidade:

- gerar e persistir `Prediction` a partir de um modelo treinado e dataset preparado.

Input sugerido:

- `model_ref`
- `dataset_ref`
- `prediction_window`
- `threshold_policy`
- `replace_existing`

Output sugerido:

- `prediction_run_id`
- `predictions_generated`
- `buy_signals_generated`
- `storage_ref`
- `success`

Dependencias abstratas:

- predictor/model runtime
- prediction repository

Mapeamento legado:

- `get_predictions(...)`
- `save_predictions_to_db(...)`
- parte final de `train_model_pipeline`

## 3.5 `run_backtest`

Tipo:

- command

Finalidade:

- executar simulacao historica completa com risco, estrategia, LLM, trades e summary oficial.

Input sugerido:

- `strategy_name`
- `prediction_source_ref`
- `dataset_ref`
- `initial_capital_usd`
- `start_date`
- `end_date`
- `backtest_days`
- `enable_llm`
- `environment`

Output sugerido:

- `run_id`
- `backtest_result`
- `simulation_summary`
- `trade_count`
- `position_count`
- `warnings`
- `success`

Dependencias abstratas:

- dataset provider
- prediction repository
- strategy runner
- trade repository
- summary repository
- LLM decision port

Mapeamento legado:

- `backend/src/system_runner.py::run_simulation`
- `backend/src/system_runner.py::run_trading_system`

## 3.6 `build_dashboard_snapshot`

Tipo:

- query

Finalidade:

- montar payload consolidado para dashboard e control center sem disparar simulacao, treino ou sync pesado.

Input sugerido:

- `run_id`
- `include_trade_history`
- `include_positions`
- `include_indicators`

Output sugerido:

- `dashboard_snapshot`
- `summary`
- `trades`
- `positions`
- `indicators`
- `health`

Dependencias abstratas:

- summary repository
- trades query repository
- positions query repository
- indicators query provider
- rpc health provider

Mapeamento legado:

- `/api/simulation`
- `/api/system/health`
- `/api/system/indicators`
- `/api/system/logs`

## 4. Queries Operacionais Secundarias

Estas queries nao sao o centro do dominio, mas continuam necessarias:

- `get_simulation_status`
- `get_trade_history`
- `get_positions`
- `get_market_analysis`
- `get_backtest_period`
- `get_treasuries_summary`

Regra:

- todas devem ser query pura;
- nenhuma deve chamar `run_trading_system()`.

## 5. Separacao de DTOs

## 5.1 DTO de comando

Caracteristicas:

- expressa intencao de executar trabalho;
- pode conter flags operacionais;
- retorna `success`, `warnings`, `run_id` e artefatos produzidos.

Exemplos:

- `RunBacktestInput`
- `RunBacktestOutput`
- `TrainModelInput`
- `TrainModelOutput`

## 5.2 DTO de consulta

Caracteristicas:

- expressa filtro de leitura;
- nao altera estado;
- deve ser seguro para repeticao.

Exemplos:

- `BuildDashboardSnapshotInput`
- `GetTradeHistoryInput`

## 5.3 DTO de resposta

Caracteristicas:

- shape orientado ao consumidor do caso de uso;
- nao e schema HTTP nem tabela do banco;
- pode ser adaptado para API ou CLI.

## 6. Mapeamento do Legado para os Casos de Uso

## 6.1 `api.py`

Mapeamento recomendado:

- rotas HTTP deixam de chamar funcoes monoliticas diretamente;
- passam a invocar:
  - `sync_market_data`
  - `train_model`
  - `generate_predictions`
  - `run_backtest`
  - `build_dashboard_snapshot`
  - queries operacionais puras

## 6.2 `system_runner.py`

Mapeamento recomendado:

- `train_model_pipeline` se divide em:
  - `prepare_features`
  - `train_model`
  - `generate_predictions`
- `run_simulation` converge para:
  - `run_backtest`
- `run_trading_system` deixa de ser caso de uso canonico;
- permanece temporariamente apenas como adaptador legado, se necessario.

## 6.3 `accumulator.py`

Mapeamento recomendado:

- logica de decisao migra para contratos de dominio:
  - `RiskSnapshot`
  - `PortfolioState`
  - `LLMDecision`
  - `StrategyDecision`
- side effects no engine ficam fora do contrato de decisao.

## 6.4 `trading_data.py`

Mapeamento recomendado:

- repositorios separados para:
  - trades
  - positions
  - simulation summaries
- payload de apresentacao deixa de morar na persistencia.

## 7. O Que Fica no Legado Temporariamente

- `run_trading_system()` como adaptador de compatibilidade, se ainda houver consumidor dependente;
- estruturas de tabela atuais;
- `TradingEngine` e estrategias legadas enquanto a Fase 2 nao extrair o nucleo puro;
- BFF/frontend atuais, desde que consumam contratos estaveis.

## 8. Primeiro Corte Tecnico Recomendado

Sequencia de implementacao sugerida:

1. criar `RunBacktestInput/Output`
2. criar `BuildDashboardSnapshotInput/Output`
3. criar contratos de repositories para `ml_predictions`, `trades` e `simulation_summary`
4. adaptar `api.py` para chamar apenas casos de uso novos nessas duas trilhas

## 9. Conclusao

Com esses casos de uso, a reescrita deixa de ser "mexer em arquivos grandes" e passa a ser "migrar fluxos explicitamente nomeados".

Esse e o ponto que conecta a Fase 1 a implementacao da Fase 2.

