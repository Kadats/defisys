# Fase 0: Mapa de Fluxos

## 1. Objetivo

Descrever os fluxos principais do sistema atual para separar:

- o que e fluxo essencial do produto;
- o que e acoplamento acidental;
- o que precisa de paridade na reescrita;
- o que pode ser corrigido ja na Fase 1.

## 2. Leitura Executiva

O backend atual opera em tres trilhas principais:

- sincronizacao de dados de mercado;
- preparo + treino + geracao de predicoes;
- simulacao/backtest + consolidacao de resultados.

Em paralelo, existe uma trilha de observabilidade/painel:

- health de RPC;
- logs;
- indicadores;
- ticker WebSocket.

O problema central nao e falta de fluxo, e sim sobreposicao entre eles:

- `get_full_prepared_data()` coleta e prepara dados no mesmo caminho;
- `run_trading_system()` recompila o pipeline inteiro;
- algumas rotas de consulta ainda podem disparar execucao pesada;
- parte da superficie "real-time" do frontend ainda depende de mock ou fallback.

## 3. Fluxo 1: Sync de Dados de Mercado

### Entrada principal

- startup do FastAPI em `backend/src/api.py`
- funcao `startup_sync_market_data()`
- chama `sync_market_data()` em threadpool

### Passos observados

1. abre conexao com banco;
2. garante criacao de tabelas de mercado, posicoes e predicoes;
3. calcula timestamps iniciais por tabela;
4. coleta dados de fontes externas:
   - Binance spot klines
   - Fear & Greed
   - Blockchair on-chain
   - Binance funding rate
   - Binance open interest
   - Deribit implied volatility
   - Uniswap/TheGraph
5. salva cada lote nas respectivas tabelas;
6. encerra sem calcular ML nem backtest.

### Observacoes importantes

- o startup atual faz trabalho pesado automaticamente;
- isso melhora "freshness", mas aumenta acoplamento entre disponibilidade da API e coleta externa;
- o fluxo e observavel, mas ainda pouco configuravel.

## 4. Fluxo 2: Preparo de Dados e Features

### Entrada principal

- `get_full_prepared_data()` em `backend/src/data/pipeline.py`

### Passos observados

1. garante novamente a existencia das tabelas;
2. repete coleta incremental das mesmas fontes do sync;
3. carrega klines do banco;
4. calcula indicadores tecnicos:
   - RSI
   - EMA 50
   - SMA 200
   - Bollinger Bands / BB Width
5. carrega e faz merge de fontes auxiliares;
6. normaliza timestamps e faz alinhamento temporal;
7. prepara dataset final com features e alvo para ML.

### Observacoes importantes

- o pipeline mistura coleta, leitura, merge, indicadores e preparacao de dataset;
- isso dificulta testar cada etapa isoladamente;
- para a Fase 1, este fluxo precisa ser quebrado em casos de uso separados.

## 5. Fluxo 3: Treino do Modelo e Geracao de Predicoes

### Entrada principal

- `POST /api/model/train`
- chama `train_model_pipeline()`

### Passos observados

1. carrega dataset preparado via `get_full_prepared_data()`;
2. aplica split temporal em `ML_TRAIN_SPLIT_DATE`;
3. treina o modelo via `train_prediction_model(...)`;
4. gera predicoes historicas via `get_predictions(...)`;
5. limpa `ml_predictions`;
6. persiste novas predicoes no banco;
7. retorna relatorio simples para a API.

### Observacoes importantes

- hoje "gerar predicoes" nao e um caso de uso independente: ele vem embutido no treino;
- isso e suficiente para o legado, mas limita evolucao para retrain parcial, refresh incremental ou batch assinado por run id.

## 6. Fluxo 4: Simulacao / Backtest Isolado

### Entrada principal

- `POST /api/simulation/run`
- chama `run_simulation(...)`

### Passos observados

1. limpa dados anteriores de simulacao:
   - `trades`
   - `positions_log`
   - `simulation_summary`
2. carrega `ml_predictions` do banco;
3. recarrega dataset preparado via `get_full_prepared_data()`;
4. faz merge entre candles/features e predicoes;
5. filtra janela temporal por split, `backtest_days`, `start_date`, `end_date`;
6. instancia `TradingEngine`;
7. instancia estrategia selecionada;
8. executa `engine.run(...)`;
9. salva trades;
10. calcula benchmark, token ROI, alpha, drawdown e sharpe;
11. salva `simulation_summary`;
12. retorna `backtest_report`.

### Observacoes importantes

- este fluxo depende explicitamente da tabela `ml_predictions`;
- o summary oficial no banco e parte do contrato da simulacao;
- a limpeza global das tabelas antes de rodar e simples, mas perigosa para concorrencia futura.

## 7. Fluxo 5: Execucao All-in-One do Legado

### Entrada principal

- `run_trading_system(...)`
- usado por consultas legadas e por execucao manual em `backend/src/main.py`

### Passos observados

1. limpa dados de simulacao;
2. chama `get_full_prepared_data()`;
3. treina modelo;
4. gera predicoes;
5. salva predicoes;
6. corta janela de backtest;
7. executa `TradingEngine`;
8. salva trades;
9. salva summary oficial;
10. retorna relatorio.

### Observacoes importantes

- este e o maior ponto de acoplamento do backend atual;
- ele recompila todo o pipeline em um unico comando;
- no legado, algumas rotas GET ainda podem cair aqui como fallback, o que viola separacao entre query e command.

## 8. Fluxo 6: Dashboard e Control Center

### Entradas principais

- BFF em `frontend/src/app/api/system/*`
- BFF em `frontend/src/app/api/sandbox/run`
- WebSockets `/api/ws/pulse` e `/api/ws/ticker`

### Passos observados

1. frontend consulta health, indicators e logs via rotas internas;
2. estas rotas fazem proxy para o backend e aplicam fallback local se falhar;
3. pagina `pulse` consome logs por WebSocket;
4. `TickerHeader` e dashboard consomem ticker por WebSocket;
5. `sandbox` chama endpoint HTTP de simulacao fake controlada por payload.

### Observacoes importantes

- `pulse` e logs sao funcionalmente reais;
- `ticker` ainda e mockado no backend;
- o BFF melhora experiencia do frontend, mas mascara erros reais do backend com payloads de fallback.

## 9. Conclusoes para a Reescrita

Fluxos que precisam de paridade funcional:

- sync de mercado;
- preparo de features;
- treino + persistencia de predicoes;
- simulacao com summary oficial;
- health/logs/indicadores do painel.

Fluxos que precisam ser corrigidos, nao preservados literalmente:

- query HTTP disparando `run_trading_system()`;
- coleta de dados embutida dentro de `get_full_prepared_data()`;
- pipeline all-in-one como dependencia de consulta;
- ticker mockado tratado como se fosse realtime real.

Recomendacao de entrada para a Fase 1:

- separar explicitamente os casos de uso:
  - `sync_market_data`
  - `prepare_features`
  - `train_model`
  - `generate_predictions`
  - `run_backtest`
  - `build_dashboard_snapshot`

