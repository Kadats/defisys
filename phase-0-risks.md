# Fase 0: Riscos e Debt Tecnico

## 1. Objetivo

Consolidar os principais riscos estruturais do repositorio e priorizar o debt tecnico que precisa orientar a reescrita parcial guiada.

## 2. Leitura Executiva

Os riscos mais relevantes do estado atual nao estao em "algoritmo ruim" ou "linguagem errada". Eles estao em cinco classes:

- monolitos com responsabilidades misturadas;
- acoplamento alto entre web, dominio, dados e runtime;
- mocks e placeholders convivendo com fluxos que parecem produtivos;
- contratos de consulta com side effect pesado;
- suite de testes que ainda nao protege a migracao com a confiabilidade necessaria.

Conclusao pratica:

- a base tem valor real e deve ser reaproveitada;
- o schema e a tese de produto estao bons o suficiente;
- o debt esta concentrado na forma de orquestrar, expor e testar o sistema.

## 3. Monolitos Principais

## 3.1 `backend/src/api.py` (`1063` linhas)

Impacto:

- concentra rotas HTTP, WebSockets, startup, leitura de banco, cache global, fallback de consulta e orquestracao operacional;
- mistura query, command, observabilidade e bootstrap no mesmo arquivo;
- aumenta muito o risco de regressao a cada mudanca pequena.

Risco:

- `critico`

## 3.2 `backend/src/strategies/accumulator.py` (`826` linhas)

Impacto:

- encapsula boa parte da logica central do produto;
- acumula regras de risco, acao, fallback, uso de LLM e comportamento de portfolio.

Risco:

- `alto`

Observacao:

- e um dos arquivos de maior valor de dominio, mas precisa ser fatiado sem perder intencao.

## 3.3 `backend/src/system_runner.py` (`616` linhas)

Impacto:

- mistura casos de uso de treino, simulacao e fluxo all-in-one;
- calcula metricas, faz limpeza de persistencia, instancia engine, estrategia e salva resultados.

Risco:

- `critico`

## 3.4 `backend/src/config.py` (`311` linhas)

Impacto:

- concentra configuracoes de ambiente, trading, risco, ML e LLM em um unico modulo;
- favorece acoplamento por leitura global de constantes.

Risco:

- `alto`

## 3.5 Frontend placeholder / laboratorio

Arquivos relevantes:

- `frontend/src/app/page.tsx` (`65` linhas)
- `frontend/src/app/login/page.tsx` (`13` linhas)
- `frontend/src/app/dashboard/pulse/page.tsx` (`220` linhas)
- `frontend/src/app/dashboard/sandbox/page.tsx` (`285` linhas)

Impacto:

- parte da UI principal ainda parece prototipo, starter template ou laboratorio;
- a sensacao de "produto" no frontend nao acompanha a sofisticacao do backend.

Risco:

- `medio`

## 4. Acoplamentos Criticos

## 4.1 Camada web lendo banco diretamente

Evidencias:

- `backend/src/api.py`
- `backend/src/services/analytics.py`
- `backend/src/data/pipeline.py`

Sinais observados:

- `storage.create_connection()`
- `pandas.read_sql(...)`
- SQL solto perto da borda HTTP

Impacto:

- dificulta teste de contrato;
- prende a API ao schema fisico;
- piora a migracao para repositories formais.

## 4.2 Consulta HTTP disparando execucao pesada

Evidencias observadas em `backend/src/api.py`:

- `/api/v1/summary`
- `/api/v1/trade_history`
- `/api/v1/backtest_period`

Impacto:

- viola separacao entre query e command;
- torna comportamento dificil de prever;
- gera risco operacional e semantico para frontend e futuros clientes.

## 4.3 Pipeline de dados com responsabilidades misturadas

Evidencia:

- `backend/src/data/pipeline.py`

Impacto:

- coleta, leitura, merge, indicadores e preparacao de dataset vivem no mesmo fluxo;
- nao ha fronteira clara entre ingestao, feature engineering e leitura analitica.

## 4.4 Persistencia contendo logica de negocio

Evidencia:

- `backend/src/data/storage/trading_data.py`
- `save_trades(...)`

Impacto:

- funcoes de storage recalculam informacao de apresentacao e PnL virtual;
- isso deveria viver em dominio ou aplicacao, nao na camada de persistencia.

## 4.5 Suite de testes acoplada ao banco principal

Evidencia:

- `tests/conftest.py`

Impacto:

- os testes copiam dados do banco principal para o banco de teste;
- isso reduz reprodutibilidade;
- isso cria dependencia operacional em um estado externo da base.

## 5. Mocks, Placeholders e Fallbacks Perigosos

## 5.1 `WS /api/ws/ticker` mockado em runtime

Evidencia:

- `backend/src/api.py`

Comportamento observado:

- gera preco sintetico com ruido aleatorio;
- parece realtime para o frontend, mas nao representa runtime real.

Risco:

- `alto`

## 5.2 `POST /api/sandbox/run` devolvendo simulacao fake

Evidencia:

- `backend/src/api.py`

Risco:

- `medio`

Observacao:

- o endpoint pode continuar existindo como laboratorio, mas precisa ser rotulado como mock sem ambiguidade.

## 5.3 BFF do frontend mascarando falhas do backend

Evidencias:

- `frontend/src/app/api/system/health/route.ts`
- `frontend/src/app/api/system/indicators/route.ts`
- `frontend/src/app/api/system/logs/route.ts`
- `frontend/src/app/api/sandbox/run/route.ts`

Impacto:

- melhora resiliencia da UI;
- piora detectabilidade de falhas reais durante a migracao.

## 5.4 Home e login ainda em estado de placeholder

Evidencias:

- `frontend/src/app/page.tsx` ainda e o starter do Next
- `frontend/src/app/login/page.tsx` contem comentario de placeholder

Impacto:

- desvia foco do que realmente e contrato de produto;
- aumenta ruido sem valor na superficie do repo.

## 6. Riscos de Migracao

## 6.1 Quebra de contrato por duplicidade de namespaces

Hoje coexistem:

- `/api/*`
- `/api/v1/*`

Risco:

- refatorar sem mapa de compatibilidade pode quebrar o frontend e consumidores legados.

## 6.2 Regressao quantitativa por mudar pipeline sem golden scenarios

Risco:

- alteracoes em pipeline, split temporal ou merge de features podem mudar sinais e resultados sem ficar claro se foi correcao ou bug.

Mitigacao:

- usar baseline definida em `phase-0-tests.md`;
- registrar cenarios de ouro com janela, seed e capital conhecidos.

## 6.3 Concorrencia e limpeza global de tabelas

Evidencia:

- `DELETE FROM trades`
- `DELETE FROM positions_log`
- `DELETE FROM simulation_summary`

Risco:

- o desenho atual funciona para um fluxo serial;
- quebra facil se houver duas simulacoes ou dois consumidores concorrentes no futuro.

## 6.4 Startup pesado dependente de provedores externos

Evidencia:

- `startup_sync_market_data()` chama `sync_market_data()`

Risco:

- a disponibilidade percebida da API fica ligada a sincronizacao externa;
- falhas de terceiros invadem o bootstrap do servidor.

## 6.5 Testes insuficientes para guiar reescrita agressiva

Risco:

- sem isolar testes de dominio e persistencia, a equipe pode "achar" que manteve comportamento quando so manteve mocks.

## 7. Priorizacao do Debt Tecnico

## P0. Resolver primeiro

- separar query de command nas rotas publicas;
- extrair casos de uso de `system_runner.py`;
- quebrar `get_full_prepared_data()` em contratos menores;
- remover dependencia do banco principal nos testes;
- explicitar contrato do LLM e do fallback.

## P1. Resolver na sequencia

- reduzir responsabilidades de `api.py`;
- mover logica de negocio para fora de `storage/trading_data.py`;
- versionar melhor a superficie publica da API;
- tornar startup de sync configuravel e observavel.

## P2. Pode esperar ate estabilizar o nucleo

- limpar placeholders do frontend;
- substituir mocks de laboratorio por contratos mais honestos;
- reorganizar configuracao monolitica em subdominios.

## 8. O Que Fica, O Que Migra, O Que Tende a Morrer

## Fica

- PostgreSQL como base principal;
- pipeline quantitativo e regras de risco como intencao de negocio;
- `ml_predictions` e `simulation_summary` como conceitos centrais;
- papel do LLM na tomada de decisao;
- health/logs/indicadores como superficie de operacao.

## Migra

- regras de dominio hoje espalhadas em `api.py`, `system_runner.py`, `accumulator.py` e `storage`;
- leituras de banco para repositories/casos de uso;
- contratos HTTP para uma superficie mais limpa e previsivel;
- fluxo all-in-one para comandos explicitos.

## Tende a morrer

- GET que chama `run_trading_system()`;
- ticker realtime mockado como se fosse real;
- home starter e login placeholder;
- dependencia de `pandas.read_sql` dentro da camada web;
- setup de testes que copia dados do banco principal.

## 9. Recomendacao de Entrada para a Fase 1

Abrir a Fase 1 com este corte:

1. definir contratos canonicos de dominio para candle, features, predicao, decisao, trade e summary;
2. separar commands e queries da API alvo;
3. desenhar casos de uso explicitos para sync, treino, predicao, backtest e dashboard snapshot;
4. fixar baseline de testes em cima destes contratos.

