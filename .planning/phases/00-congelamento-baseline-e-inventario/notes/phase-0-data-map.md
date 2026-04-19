# Fase 0: Mapa de Dados

## 1. Objetivo

Mapear a camada de dados atual do DefiSys para responder:

- quais tabelas existem de fato;
- quem escreve e quem le cada tabela;
- como os ambientes sao separados;
- onde o banco vaza para dentro da camada de aplicacao e da camada web;
- quais partes precisam ser abstraidas na reescrita.

## 2. Leitura Executiva

O sistema hoje usa PostgreSQL como fonte principal de persistencia para:

- historico de mercado;
- dados auxiliares de sentimento/derivativos/DeFi;
- predicoes de ML;
- logs de posicoes;
- trilha de trades;
- resumo oficial de simulacao.

O desenho de dados tem uma base funcional clara, mas o acesso esta fortemente acoplado ao codigo:

- `psycopg2` espalhado;
- SQL solto em multiplos modulos;
- `pandas.read_sql` fora de repositories formais;
- leitura direta do banco em `api.py`, `pipeline.py` e `services/analytics.py`;
- testes que ainda tentam buscar dados do banco principal.

Conclusao tecnica:

- o modelo de dados atual pode ser reaproveitado em grande parte;
- a camada de acesso precisa ser redesenhada quase por completo.

## 3. Ambientes de Banco

Separacao observada em `docker-compose.yml`:

- `defisys`
  - banco principal
  - porta `5432`
  - uso esperado: historico, treino, simulacoes oficiais
- `defisys_test`
  - banco de testes
  - porta `5433`
  - uso esperado: `pytest`
- `defisys_paper_trading`
  - banco de paper trading
  - porta `5434`
  - uso esperado: forward testing

Estado atual:

- a separacao de ambientes existe na infraestrutura;
- o codigo de aplicacao ainda depende basicamente de `DATABASE_URL`;
- o uso do banco de paper trading ainda nao aparece como fluxo de primeira classe na aplicacao;
- os testes ainda mostram acoplamento indevido ao banco principal.

## 4. Tabelas Identificadas

## 4.1 Tabelas de Mercado

### `btcusdt_4h_klines` ou `{symbol}_{interval}_klines`

- ownership fisico:
  - `backend/src/data/storage/market_data.py`
- criacao:
  - `create_klines_table`
- escrita:
  - `save_klines_to_db`
- leitura:
  - `get_data_from_db`
  - leitura direta em `api.py` para `/api/history`
  - leitura no pipeline de preparo
- papel:
  - base principal de candles OHLCV;
  - insumo de indicadores, features, graficos e analises.

### `fear_and_greed_index`

- criacao:
  - `create_fng_table`
- escrita:
  - `save_fng_to_db`
- leitura:
  - `get_fng_data_from_db`
  - merge no pipeline
- papel:
  - serie auxiliar de sentimento macro de mercado.

### `bitcoin_on_chain_metrics`

- criacao:
  - `create_on_chain_table`
- escrita:
  - `save_on_chain_to_db`
- leitura:
  - uso esperado via pipeline, mas com presenca menos evidente no consumo final
- papel:
  - dados on-chain agregados.

### `binance_futures_funding_rate`

- criacao:
  - `create_funding_rate_table`
- escrita:
  - `save_funding_rate_to_db`
- leitura:
  - leitura direta com `pd.read_sql` em `data/pipeline.py`
- papel:
  - input para features derivativas.

### `binance_futures_open_interest`

- criacao:
  - `create_open_interest_table`
- escrita:
  - `save_open_interest_to_db`
- leitura:
  - leitura direta com `pd.read_sql` em `data/pipeline.py`
- papel:
  - input para features derivativas.

### `implied_volatility`

- criacao:
  - `create_implied_volatility_table`
- escrita:
  - `save_implied_volatility_to_db`
- leitura:
  - entra no pipeline de coleta, mas aparece menos no consumo consolidado atual
- papel:
  - insumo auxiliar de volatilidade.

### `uniswap_pool_data`

- criacao:
  - `create_uniswap_pool_table`
- escrita:
  - `save_uniswap_pool_data_to_db`
- leitura:
  - `get_uniswap_pool_data_from_db`
  - merge no pipeline
- papel:
  - dados de volume e TVL do pool usado como sinal.

## 4.2 Tabelas de ML

### `ml_predictions`

- criacao:
  - `create_ml_predictions_table`
- escrita:
  - `save_predictions_to_db`
- limpeza:
  - `clear_predictions_data`
- leitura:
  - `get_predictions_from_db`
  - leitura em `data/pipeline.py`
  - leitura indireta e direta em `api.py`
- papel:
  - guardar sinais gerados pelo modelo e metricas auxiliares como `prediction_correct`.

Observacoes:

- a tabela e tratada como artefato central entre treino e simulacao;
- a simulacao depende dela explicitamente;
- isso reforca a necessidade de um caso de uso formal `generate_predictions`.

## 4.3 Tabelas de Execucao / Simulacao

### `positions_log`

- criacao:
  - `create_positions_log_table`
- escrita:
  - `log_open_position`
  - `log_close_position`
- leitura:
  - `get_positions_from_db`
  - consultas em `api.py`
- papel:
  - log de posicoes abertas/fechadas, principalmente LPs.

### `trades`

- criacao:
  - `create_trades_table`
- escrita:
  - `save_trades`
- limpeza:
  - `clear_simulation_data`
- leitura:
  - `services/analytics.py`
  - consumo indireto via `/api/simulation`
- papel:
  - trilha detalhada de transacoes;
  - base para construir KPIs e historico exibido pela UI.

Observacoes:

- `save_trades` faz mais que persistencia:
  - apaga dados antigos;
  - recalcula PnL virtual para posicoes abertas;
  - injeta detalhes para apresentacao;
- isso e um forte sinal de mistura entre dominio, aplicacao e persistencia.

### `simulation_summary`

- criacao:
  - `create_simulation_summary_table`
- escrita:
  - `save_simulation_summary`
- leitura:
  - `get_latest_simulation_summary`
  - `api.py`
- papel:
  - fonte oficial de verdade para resumo de simulacao.

Campos relevantes observados:

- `total_equity`
- `roi_percent`
- `benchmark_roi_percent`
- `total_trades`
- `initial_capital`
- `cash_balance`
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
- `token_roi`
- `alpha_vs_hold`

Observacoes:

- esta tabela e a ancora mais importante do dashboard e da API de resumo;
- deve continuar existindo na reescrita, ainda que por tras de outro repository/mapper;
- e uma boa candidata a “query model” oficial do backtest.

## 4.4 Tabela Social / LLM

### `sentiment_logs`

- criacao:
  - `create_sentiment_table`
- escrita:
  - `insert_sentiment_log`
- leitura:
  - nao apareceu integrada no fluxo principal observado
- papel:
  - armazenar log de sentimento produzido por analise externa, incluindo modelo usado e resposta bruta.

Observacoes:

- hoje parece subutilizada;
- pode virar tabela importante se o pipeline de LLM/sentimento for formalizado;
- tambem pode ser tratada como artefato experimental caso nao participe do fluxo principal.

## 5. Ownership Real por Modulo

## 5.1 Infraestrutura de escrita

Principais pontos de escrita:

- `backend/src/data/storage/market_data.py`
- `backend/src/data/storage/ml_data.py`
- `backend/src/data/storage/trading_data.py`
- `backend/src/data/storage/social_data.py`

## 5.2 Orquestracao de escrita

Quem decide quando gravar:

- `backend/src/data/pipeline.py`
  - coleta e atualiza dados de mercado;
- `backend/src/system_runner.py`
  - salva predições, trades e summary;
- `backend/src/core/trading_engine.py`
  - escreve em `positions_log` por chamadas internas.

## 5.3 Leitura distribuida

Quem le o banco fora da camada de storage:

- `backend/src/api.py`
- `backend/src/data/pipeline.py`
- `backend/src/services/analytics.py`
- `tests/conftest.py`

Conclusao:

- nao existe uma camada unica de consulta;
- varias leituras furam a fronteira da persistencia.

## 6. Fluxo de Dados Atual

## 6.1 Mercado -> Banco

Fluxo observado:

1. `sync_market_data()`
2. coleta fontes externas
3. garante criacao das tabelas
4. grava dados em tabelas de mercado

## 6.2 Banco -> Features

Fluxo observado:

1. `get_full_prepared_data()`
2. recarrega candles e dados auxiliares do banco
3. calcula indicadores tecnicos
4. faz merges com funding, open interest e Uniswap
5. aplica `shift(1)` nas features
6. gera `Target_Trend`

Observacao importante:

- o pipeline mistura coleta, leitura, enriquecimento, feature engineering e preparo de target num unico fluxo grande.

## 6.3 Features -> Predicoes

Fluxo observado:

1. `train_model_pipeline()`
2. treina modelo com dados preparados
3. `get_predictions()`
4. `save_predictions_to_db()`

## 6.4 Predicoes + Mercado -> Simulacao

Fluxo observado:

1. `run_simulation()`
2. limpa `trades`, `positions_log` e `simulation_summary`
3. le `ml_predictions`
4. le dados preparados
5. faz merge
6. executa estrategia e engine
7. salva `trades`
8. salva `simulation_summary`

## 7. Vazamentos Arquiteturais

Os principais vazamentos encontrados:

### Vazamento A. Camada web lendo banco diretamente

Exemplos:

- `GET /api/history`
- partes de `api.py` consultando dados, summaries e cache

Impacto:

- API deixa de ser casca fina;
- aumenta acoplamento a schema fisico.

### Vazamento B. Pipeline usando SQL ad hoc fora de repositories

Exemplos:

- `pd.read_sql` para `funding_rate` e `open_interest`
- `pd.read_sql` para `positions_log`
- `pd.read_sql` para `ml_predictions`

Impacto:

- consultas ficam espalhadas;
- dificulta evolucao de schema;
- mistura responsabilidade de aplicacao e persistencia.

### Vazamento C. Persistencia fazendo logica de negocio

Exemplo:

- `save_trades()` recalcula PnL virtual e injeta semantica de posicao aberta.

Impacto:

- repository deixa de ser persistencia e vira motor parcial de dominio/apresentacao.

### Vazamento D. Testes dependentes de banco principal

Em `tests/conftest.py`:

- tentativa de ler ultimos dados da base principal;
- copia parcial para o banco de teste.

Impacto:

- baixa reprodutibilidade;
- risco operacional;
- regressao pouco confiavel.

## 8. Classificacao das Tabelas para a Reescrita

## 8.1 Manter com alta probabilidade

- `btcusdt_4h_klines` / tabela equivalente de candles
- `ml_predictions`
- `positions_log`
- `trades`
- `simulation_summary`
- `fear_and_greed_index`
- `binance_futures_funding_rate`
- `binance_futures_open_interest`
- `uniswap_pool_data`

## 8.2 Manter, mas revisar papel

- `bitcoin_on_chain_metrics`
- `implied_volatility`
- `sentiment_logs`

## 8.3 Requerem modelagem melhor

- qualquer tabela ou consulta que sirva simultaneamente para:
  - dominio
  - analytics
  - apresentacao

`simulation_summary` deve permanecer, mas como projection oficial bem definida.

## 9. Recomendacoes para Fase 4

Decisoes recomendadas para a futura camada de persistencia:

- criar repositories formais por agregado:
  - market data
  - predictions
  - positions
  - trades
  - simulation summaries
  - sentiment / llm logs
- mover leitura analitica para query services dedicados;
- remover `pd.read_sql` da camada web;
- mover qualquer calculo de negocio para dominio ou application services;
- tratar `simulation_summary` como query model oficial e nao como tabela “quebra-galho”.

## 10. Recomendacoes para Fase 7

- eliminar a populacao do banco de teste a partir da base principal;
- criar fixtures sinteticas para candles, predicoes e summaries;
- definir um dataset pequeno e deterministico para comparacao de backtest.

## 11. Conclusao

O banco atual ja expressa bem a historia do produto:

- mercado coletado;
- modelo treinado;
- sinais persistidos;
- simulacao executada;
- resultado consolidado.

O maior problema nao e o schema fisico em si. O maior problema e que o acesso a esse schema esta espalhado e atravessa camadas demais.

Resumo:

- o modelo de dados pode ser preservado em boa parte;
- o acesso precisa ser reestruturado;
- a reescrita parcial deve atacar primeiro contratos e ownership, nao necessariamente renomear tabelas.

## 12. Status do Entregavel

- status: `draft-initial`
- pronto para servir como baseline da camada de dados na Fase 0
