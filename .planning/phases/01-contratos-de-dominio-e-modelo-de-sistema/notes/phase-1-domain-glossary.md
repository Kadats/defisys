# Fase 1: Glossario de Dominio

## 1. Objetivo

Definir a linguagem canonica do sistema para que a reescrita passe a discutir contratos, testes e implementacao com os mesmos nomes.

## 2. Leitura Executiva

Hoje o repositrio usa nomes de tres origens ao mesmo tempo:

- nomes orientados a dados e coluna de DataFrame;
- nomes orientados a estrategia e runtime;
- nomes orientados a API e dashboard.

O objetivo deste glossario e reduzir traducao mental entre essas camadas.

Diretriz principal:

- o nome canonico deve refletir o conceito de negocio;
- nomes legados continuam existindo apenas como referencia de migracao;
- DTO, entidade e view model nao devem disputar o mesmo vocabulario.

## 3. Termos Canonicos

## 3.1 MarketCandle

Definicao:

- unidade canonica de mercado em serie temporal fechada;
- representa um candle fechado pronto para analise.

Inclui conceitualmente:

- timestamp de abertura/fechamento;
- open, high, low, close, volume;
- simbolo e timeframe.

Termos legados relacionados:

- `klines`
- `btcusdt_4h_klines`
- colunas `Open_time`, `Close`, `Volume`
- `OHLCV`

Regra:

- `MarketCandle` e dado bruto de mercado, nao feature e nao predicao.

## 3.2 FeatureVector

Definicao:

- conjunto de sinais derivados disponiveis no momento da decisao para ML e policy.

Inclui conceitualmente:

- indicadores tecnicos;
- dados auxiliares de derivativos, sentimento e DeFi;
- features calculadas com causalidade temporal preservada.

Termos legados relacionados:

- `prepared data`
- `full_df`
- `full_df_with_predictions` antes do merge com predicao deve ser entendido como dataset de features
- colunas como `RSI`, `EMA_50`, `BB_Width`, `FNG_Value`

Regra:

- `FeatureVector` nao e o candle em si;
- `FeatureVector` nao deve conter target nem resultado futuro.

## 3.3 Prediction

Definicao:

- saida do modelo quantitativo para uma unidade temporal observavel.

Inclui conceitualmente:

- classe prevista;
- confianca;
- metadados do modelo e do horizonte, quando disponiveis.

Termos legados relacionados:

- `prediction`
- `prediction_proba`
- `ml_predictions`
- `prediction_correct`

Regra:

- `Prediction` nao e decisao de trade;
- e um insumo de decisao.

## 3.4 MarketRegime

Definicao:

- classificacao do estado de mercado usada para veto, roteamento ou postura defensiva.

Termos legados relacionados:

- `regime`
- `market_regime`
- `UNCERTAIN`
- `bull`, `bear`, `sideways`

Regra:

- regime nao substitui predicao;
- regime complementa e restringe a decisao.

## 3.5 RiskSnapshot

Definicao:

- fotografia do estado de risco da carteira e do sistema no momento da decisao.

Inclui conceitualmente:

- health factor;
- drawdown atual;
- exposicao e alavancagem;
- reserva minima de caixa;
- travas e alertas ativos.

Termos legados relacionados:

- `health_factor`
- `HF_WARNING`
- `HF_CRITICAL`
- `MAX_GLOBAL_DRAWDOWN`
- `MAX_DAILY_DRAWDOWN`
- `RiskManager`

Regra:

- `RiskSnapshot` nao executa nada;
- ele descreve limites e estado de risco.

## 3.6 PortfolioState

Definicao:

- estado consolidado das tesourarias e exposicoes da carteira em um instante.

Inclui conceitualmente:

- caixa/spot;
- exposicao em BTC;
- alocacao em LP;
- colateral e divida em Aave;
- equity total.

Termos legados relacionados:

- `wallet_spot_usd`
- `wallet_spot_btc`
- `wallet_lp_value_usd`
- `aave_collateral_usd`
- `aave_debt_usd`
- `total_equity`

Regra:

- `PortfolioState` e o estado da carteira, nao o resultado agregado da simulacao inteira.

## 3.7 Position

Definicao:

- exposicao aberta ou historica com identidade propria, ciclo de vida e PnL associado.

Tipos conceituais esperados:

- spot accumulation;
- LP position;
- borrow/leverage position;
- short/directional position, se aplicavel.

Termos legados relacionados:

- `positions_log`
- `active_lps`
- `position_id`
- `open_timestamp`
- `close_timestamp`

Regra:

- `Position` tem identidade;
- `TradeRecord` e evento, nao posicao.

## 3.8 TradeRecord

Definicao:

- evento transacional registrado ao longo da execucao simulada.

Inclui conceitualmente:

- timestamp;
- acao executada;
- quantidade;
- preco ou valor relevante;
- saldo/equity apos a acao quando aplicavel.

Termos legados relacionados:

- `transaction_log`
- tabela `trades`
- `action`
- `post_trade_equity`

Regra:

- `TradeRecord` e a trilha de eventos;
- ele pode abrir, ajustar ou fechar uma `Position`.

## 3.9 StrategyDecision

Definicao:

- decisao validada que a estrategia ou policy layer emite para o motor de execucao simulada.

Inclui conceitualmente:

- acao escolhida;
- intensidade/sizing;
- motivo;
- origem da decisao;
- metadados de validacao.

Termos legados relacionados:

- `decision`
- `action`
- `amount_pct`
- `_fallback_decision`
- resposta do `llm_agent`

Regra:

- `StrategyDecision` e o primeiro contrato que pode virar acao;
- antes dele existem somente sinais e contexto.

## 3.10 LLMDecision

Definicao:

- recomendacao produzida pelo modelo generativo antes da validacao final do sistema.

Termos legados relacionados:

- `consult_risk_agent_api`
- `Gemini`
- resposta do `llm_agent`

Regra:

- `LLMDecision` nao deve ser tratada como decisao final;
- ela precisa passar por validacao e normalizacao para virar `StrategyDecision`.

## 3.11 BacktestRun

Definicao:

- execucao de simulacao historica com parametros, janela temporal e artefatos associados.

Termos legados relacionados:

- `run_trading_system()`
- `run_simulation()`
- `run_id`

Regra:

- `BacktestRun` e o contexto de execucao;
- o resultado final dessa execucao e expresso por `BacktestResult` e `SimulationSummary`.

## 3.12 BacktestResult

Definicao:

- resultado detalhado de uma execucao de backtest, voltado a analise e verificacao.

Inclui conceitualmente:

- ROI;
- benchmark;
- drawdown;
- sharpe;
- metricas de tokens;
- contagem de trades;
- datas de inicio e fim;
- metadados do run.

Termos legados relacionados:

- `backtest_results`
- `backtest_report`

Regra:

- `BacktestResult` e rico e analitico;
- nao e necessariamente o payload final do dashboard.

## 3.13 SimulationSummary

Definicao:

- resumo oficial persistivel de uma simulacao, usado como fonte de verdade para a UI e consultas de status.

Termos legados relacionados:

- `simulation_summary`
- `official_summary`
- `/api/simulation/summary`
- `/api/v1/summary`

Regra:

- `SimulationSummary` e a visao oficial persistida;
- `BacktestResult` pode conter mais detalhe do que ele.

## 3.14 DashboardSnapshot

Definicao:

- payload pronto para consumo de tela, agregando dados oficiais e metricas auxiliares.

Termos legados relacionados:

- `summary` retornado pela API
- payload de `/api/simulation`
- payload de `/api/system/indicators`

Regra:

- `DashboardSnapshot` pertence a aplicacao/interfaces;
- nao deve contaminar contratos de dominio puro.

## 4. Sinonimos e Termos Legados a Aposentar

## 4.1 Termos aceitaveis apenas durante migracao

- `full_df`
- `full_df_with_predictions`
- `official_summary`
- `transaction_log`
- `positions_log` como nome de tabela, nao como conceito
- `summary_data`

## 4.2 Termos que devem virar conceitos separados

- `prediction` versus `decision`
- `trade` versus `position`
- `backtest_report` versus `simulation_summary`
- `risk manager output` versus `portfolio state`

## 5. Regras de Nomenclatura para a Reescrita

- Entidades e value objects usam nomes do dominio, nao nomes de tabela.
- DTOs de caso de uso usam verbos de aplicacao:
  - `RunBacktestInput`
  - `RunBacktestOutput`
- View models usam nomes orientados a interface:
  - `DashboardSnapshot`
  - `IndicatorsWidgetData`
- Nomes de DataFrame e colunas deixam de definir o modelo mental do sistema.

## 6. Conclusao

Linguagem canonica recomendada para a reescrita:

- `MarketCandle`
- `FeatureVector`
- `Prediction`
- `MarketRegime`
- `RiskSnapshot`
- `PortfolioState`
- `Position`
- `TradeRecord`
- `LLMDecision`
- `StrategyDecision`
- `BacktestRun`
- `BacktestResult`
- `SimulationSummary`
- `DashboardSnapshot`

Esses termos devem servir de base para os contratos formais da Fase 1 e para a extracao do nucleo puro na Fase 2.

