# Fase 1: Modelo de Sistema

## 1. Objetivo

Descrever o modelo conceitual alvo do backend e a distribuicao correta de responsabilidades entre camadas.

## 2. Leitura Executiva

O sistema atual funciona, mas as responsabilidades estao colapsadas em poucos pontos:

- `api.py` mistura interface, bootstrap, leitura de dados e logica operacional;
- `system_runner.py` mistura casos de uso e detalhes concretos;
- `pipeline.py` mistura ingestao, merge, features e leitura analitica;
- estrategias carregam tanto dominio util quanto acoplamentos de runtime.

O modelo alvo precisa corrigir isso sem perder o que tem valor:

- regras de risco;
- logica de portfolio;
- sinais de ML;
- papel do LLM;
- summary oficial de simulacao;
- operacao do painel.

## 3. Camadas Alvo

## 3.1 Domain

Responsabilidade:

- representar o negocio de trading, risco, portfolio e decisao em codigo puro.

Pode conter:

- entidades e value objects;
- regras de sizing;
- calculos de risco;
- regras de validacao de decisao;
- composicao entre predicao, regime, snapshot de risco e decisao.

Nao pode conter:

- FastAPI;
- `psycopg2`;
- `pandas.read_sql`;
- acesso a arquivo;
- websocket;
- chamada HTTP externa;
- dependencia direta de variavel de ambiente.

Exemplos esperados:

- `PortfolioState`
- `RiskSnapshot`
- `StrategyDecision`
- regras de kill switch
- regras de health factor
- normalizacao de acoes aceitas do LLM

## 3.2 Application

Responsabilidade:

- orquestrar casos de uso com contratos claros de entrada e saida.

Pode conter:

- comandos;
- consultas;
- DTOs de input/output;
- coordenacao entre repositories, gateways e dominio;
- selecao do fluxo correto por caso de uso.

Nao pode conter:

- SQL inline;
- rota HTTP;
- detalhes de serializacao de UI;
- regra de negocio espalhada por side effect.

Casos de uso alvo:

- `sync_market_data`
- `prepare_features`
- `train_model`
- `generate_predictions`
- `run_backtest`
- `build_dashboard_snapshot`

## 3.3 Infrastructure

Responsabilidade:

- implementar portas concretas para persistencia e servicos externos.

Pode conter:

- repositories Postgres;
- gateways de Binance, TheGraph, Blockchair, Deribit;
- cliente do LLM;
- RPC manager;
- adaptadores de logging;
- leitura de arquivos e configuracao concreta.

Nao pode conter:

- regra de negocio central;
- shape final de payload HTTP;
- decisao de estrategia por conta propria.

Exemplos do legado que devem migrar para ca:

- `backend/src/data/storage/*`
- `backend/src/data/sources*`
- `backend/src/ai/llm_agent.py` na parte de integracao externa
- `backend/src/core/rpc_manager.py`

## 3.4 Interfaces

Responsabilidade:

- expor casos de uso para fora do sistema.

Pode conter:

- rotas FastAPI;
- schemas HTTP;
- handlers de websocket;
- CLI;
- BFF/frontend adapters.

Nao pode conter:

- query SQL;
- merge de DataFrame de negocio;
- fallback de simulacao pesada disparado por GET;
- regra de risco.

Exemplos do legado que devem ser reduzidos:

- `backend/src/api.py`
- `backend/src/main.py`

## 4. Fluxos Principais Mapeados para a Arquitetura Alvo

## 4.1 Sync de mercado

Interfaces:

- endpoint administrativo, job ou startup controlado

Application:

- `sync_market_data`

Infrastructure:

- market data gateways
- repository de candles e fontes auxiliares

Domain:

- validacoes minimas de integridade temporal

## 4.2 Preparo de features

Interfaces:

- comando interno ou endpoint operacional

Application:

- `prepare_features`

Infrastructure:

- repositories de market data

Domain:

- regras de causalidade
- tipos `MarketCandle` e `FeatureVector`

## 4.3 Treino e predicoes

Interfaces:

- endpoint operacional ou job

Application:

- `train_model`
- `generate_predictions`

Infrastructure:

- trainer/model gateway
- repository de predicoes

Domain:

- `Prediction`
- validacoes de confianca e rastreabilidade

## 4.4 Decisao com policy + LLM

Interfaces:

- nao deve existir como endpoint bruto de tela

Application:

- parte interna de `run_backtest` e, no futuro, de paper trading

Infrastructure:

- gateway do LLM

Domain:

- `RiskSnapshot`
- `PortfolioState`
- `LLMDecision`
- `StrategyDecision`
- validacao das acoes permitidas

## 4.5 Backtest

Interfaces:

- endpoint operacional, job ou CLI

Application:

- `run_backtest`

Infrastructure:

- repositories de leitura e persistencia

Domain:

- engine de simulacao
- regras de risco
- regras de portfolio
- `BacktestResult`
- `SimulationSummary`

## 4.6 Dashboard e control center

Interfaces:

- API HTTP
- WebSockets
- BFF do frontend

Application:

- `build_dashboard_snapshot`
- consultas de health/logs/indicators

Infrastructure:

- repositories
- log provider
- RPC health provider

Domain:

- apenas contratos de leitura necessarios;
- nada de view model de tela no dominio puro.

## 5. Mapeamento do Legado para o Modelo Alvo

## 5.1 `backend/src/api.py`

Hoje:

- startup
- HTTP
- websocket
- leitura de banco
- cache
- fallback de consulta
- acionamento de simulacao

Destino alvo:

- permanece apenas com rotas, schemas e wiring de casos de uso.

## 5.2 `backend/src/system_runner.py`

Hoje:

- treino
- simulacao
- fluxo all-in-one
- metricas
- persistencia parcial

Destino alvo:

- quebrado em casos de uso de `application`;
- calculos puros extraidos para `domain`;
- persistencia movida para `infrastructure`.

## 5.3 `backend/src/data/pipeline.py`

Hoje:

- coleta
- load
- merge
- feature engineering
- consultas de leitura

Destino alvo:

- dividido entre `application` e `infrastructure`;
- contratos puros de feature no `domain`.

## 5.4 `backend/src/strategies/accumulator.py`

Hoje:

- decisao de alocacao
- uso de LLM
- regras de risco
- side effects sobre engine

Destino alvo:

- parte de decisao vai para `domain`;
- consulta ao LLM entra por porta em `application/infrastructure`;
- side effects ficam do lado do motor de execucao simulada.

## 5.5 `backend/src/data/storage/trading_data.py`

Hoje:

- persistencia
- limpeza global
- recomputacao de dados de apresentacao

Destino alvo:

- persistencia pura em `infrastructure`;
- recomputacao e modelagem de resultado sobem para `domain` ou `application`.

## 6. Politicas de Fronteira

## 6.1 Query versus Command

Regra:

- consulta nao dispara simulacao nem treino.

Implicacao:

- `GET /api/v1/summary` e similares nao devem mais chamar `run_trading_system()`.

## 6.2 Dado persistido versus payload de tela

Regra:

- tabelas do banco nao definem shape de resposta HTTP.

Implicacao:

- `simulation_summary` e fonte oficial;
- `DashboardSnapshot` e uma montagem de aplicacao/interface.

## 6.3 Sinal quantitativo versus decisao operacional

Regra:

- predicao de ML, regime, risco e LLM sao insumos;
- apenas a decisao validada pode alimentar execucao simulada.

## 6.4 LLM como porta, nao como atalho

Regra:

- o cliente Gemini nao entra no dominio;
- a resposta bruta dele tambem nao.

Implicacao:

- o contrato do LLM precisa produzir um objeto normalizado antes de qualquer acao.

## 7. Estrutura de Diretorios Recomendada

```text
backend/src/
  domain/
    market/
    risk/
    portfolio/
    strategies/
    backtest/
  application/
    commands/
    queries/
    dto/
    services/
  infrastructure/
    db/
      repositories/
      mappers/
    market_data/
    ml/
    llm/
    rpc/
    logging/
  interfaces/
    api/
      routes/
      schemas/
      dependencies/
    websocket/
    cli/
```

## 8. O Que Sai Primeiro dos Monolitos

Primeiro corte recomendado:

- regras de risco e portfolio para `domain`;
- contratos de decisao e summary para `domain`;
- `run_backtest` como caso de uso de `application`;
- repositories de `simulation_summary`, `trades` e `ml_predictions` em `infrastructure`;
- `api.py` reduzido a chamadas de caso de uso.

## 9. Conclusao

O modelo de sistema alvo nao muda a finalidade do produto. Ele muda onde cada responsabilidade mora.

Resumo da direcao:

- `domain` decide;
- `application` orquestra;
- `infrastructure` conecta;
- `interfaces` expoe.

Com isso, a Fase 2 pode extrair codigo util sem carregar junto os acoplamentos do legado.

