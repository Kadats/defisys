# Plano de Reescrita Parcial Guiada

## 1. Objetivo

Este documento define o plano de reescrita parcial guiada do DefiSys. A meta nao e trocar tecnologia por impulso, e sim reconstruir os trechos que hoje concentram risco tecnico, mantendo o que ja tem valor comprovado: dominio de trading, regras de risco, pipeline quantitativo, testes uteis e a base operacional ja aprendida no projeto.

Direcao recomendada:

- Manter `Python + FastAPI + PostgreSQL` no backend.
- Manter `Next.js + TypeScript` no frontend.
- Tratar eventual uso de `Go` apenas como extracao futura para um executor operacional, se e somente se o produto realmente chegar em execucao continua real.
- Fazer migracao gradual, por fatias, com convivio entre legado e nova arquitetura ate haver paridade funcional.

## 2. Diagnostico Resumido

Os problemas principais observados nao apontam para falha de linguagem. Eles apontam para falta de fronteiras arquiteturais.

Principais sintomas atuais:

- Arquivos centrais grandes e multifuncionais:
  - `backend/src/api.py`
  - `backend/src/system_runner.py`
  - `backend/src/core/trading_engine.py`
  - `backend/src/strategies/accumulator.py`
  - `backend/src/config.py`
- Mistura de responsabilidades:
  - API HTTP com regra de negocio
  - websocket com mock e logica operacional
  - startup com sincronizacao de dados
  - acesso direto ao banco dentro da camada de apresentacao
  - estrategia com side effects e acoplamento a servicos externos
- Persistencia fraca:
  - uso extensivo de `psycopg2` + SQL solto + `pandas.read_sql`
  - pouca separacao entre leitura analitica, escrita transacional e schema management
- Testes pouco hermeticos:
  - fixture que tenta copiar dados do banco principal para o banco de teste
- Inconsistencias de produto e stack:
  - documentacao antiga ainda carrega sinais de arquitetura anterior
  - frontend atual e Next.js, mas o historico do repositorio ainda carrega rastros de Vue e partes placeholder
- LLM no caminho de decisao:
  - aceitavel como modo consultivo ou experimento
  - inadequado como nucleo deterministico de estrategia e backtest

## 3. Principios da Reescrita

1. Reescrever por fronteiras, nao por pasta.
2. O dominio vem antes da infraestrutura.
3. Regra de negocio deve ser deterministica e testavel.
4. API, banco, provedores externos e UI sao adaptadores, nao o centro do sistema.
5. O legado continua servindo como referencia ate a nova implementacao atingir paridade.
6. Cada fase precisa deixar o sistema em estado executavel.
7. Nao introduzir mais complexidade de stack sem necessidade comprovada.
8. LLM sai do hot path de trade/backtest e vira dependencia opcional.

## 4. Objetivos de Arquitetura

Ao final da reescrita parcial, o sistema deve ter estas propriedades:

- Dominio de trading, risco e portfolio isolado em codigo puro.
- Casos de uso explicitados: sincronizar dados, preparar dataset, treinar modelo, gerar predicoes, rodar backtest, consolidar resultados, rodar paper trading.
- Infraestrutura encapsulada por gateways e repositories.
- API fina, sem logica de negocio.
- Frontend consumindo contratos estaveis via BFF/proxy claro.
- Testes unitarios independentes de banco real.
- Testes de integracao rodando em ambiente dedicado e previsivel.
- Caminho claro de migracao para paper trading e possivel execucao real.

## 5. Nao Objetivos

Este plano nao busca, nesta etapa:

- Trocar Python por outra linguagem no nucleo quantitativo.
- Construir execucao real em corretora ou on-chain ja no inicio.
- Fazer redesign visual completo do frontend.
- Otimizar performance prematuramente.
- Adicionar novas estrategias antes da estabilizacao arquitetural.

## 6. Arquitetura-Alvo

### 6.1 Estrutura conceitual

O backend deve convergir para quatro camadas:

- `domain`
  - entidades e value objects
  - regras puras de portfolio, risco, sizing, regime, estrategia
- `application`
  - casos de uso orquestrados
  - comandos e consultas
  - contratos de entrada e saida
- `infrastructure`
  - Postgres
  - Binance
  - TheGraph
  - Gemini ou outros LLMs
  - websocket/log streaming
  - arquivos e configuracao
- `interfaces`
  - FastAPI
  - jobs
  - CLI interna
  - BFF/rotas de integracao

### 6.2 Estrutura sugerida de diretorios

Estrutura alvo sugerida:

```text
backend/src/
  domain/
    portfolio/
    risk/
    market/
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
      models/
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

### 6.3 Regras estruturais

- `domain` nao importa FastAPI, banco, requests, pandas IO ou variaveis de ambiente diretamente.
- `application` conhece contratos e abstrai repositories/gateways.
- `infrastructure` implementa adaptadores concretos.
- `interfaces` chama apenas casos de uso.

## 7. Estrategia de Migracao

Nao sera feito big bang.

Modelo de migracao:

- manter o legado funcionando;
- criar a nova arquitetura em paralelo;
- migrar primeiro o nucleo puro;
- depois plugar adaptadores;
- por fim mudar as rotas e desativar o legado.

Padrao de transicao:

1. mapear comportamento atual;
2. extrair contrato e testes;
3. implementar no novo modulo;
4. validar paridade;
5. trocar o ponto de entrada;
6. remover o legado apenas quando a cobertura estiver aceitavel.

## 8. Fases

## Fase 0. Congelamento, Baseline e Inventario

### Objetivo

Criar uma linha de base tecnica antes de mover partes criticas.

### Escopo

- congelar entradas de novas features no backend critico;
- registrar problemas conhecidos;
- catalogar endpoints, jobs, estrategias, tabelas e fluxos;
- identificar quais testes realmente validam comportamento e quais so mockam implementacao;
- definir o conjunto minimo de cenarios de regressao.

### Entregaveis

- inventario de endpoints atuais;
- inventario de tabelas atuais e uso por modulo;
- mapa dos fluxos:
  - sync de dados
  - treino de modelo
  - geracao de predicoes
  - simulacao
  - dashboard/control center
- lista de invariantes de negocio;
- lista de debt items criticos.

### Criterios de saida

- saber exatamente o que precisa continuar funcionando;
- saber o que e legado descartavel;
- definir a baseline de regressao funcional.

### Riscos

- descobrir tarde demais dependencias ocultas;
- quebrar o produto por migrar algo “parecia inutil” mas ainda estava em uso.

---

## Fase 1. Contratos de Dominio e Modelo de Sistema

### Objetivo

Definir a linguagem comum do sistema antes de mexer em implementacao.

### Escopo

- modelar entidades principais:
  - MarketCandle
  - FeatureVector
  - Prediction
  - PortfolioState
  - Position
  - StrategyDecision
  - RiskSnapshot
  - BacktestResult
- definir contratos de entrada e saida dos casos de uso;
- separar explicitamente:
  - dado bruto
  - feature
  - sinal
  - decisao
  - execucao simulada
  - resultado consolidado

### Entregaveis

- documento de contratos de dominio;
- tipos base e DTOs;
- definicao de invariantes:
  - reserva de gas
  - limites de drawdown
  - sem look-ahead
  - health factor
  - regras de leverage

### Criterios de saida

- qualquer implementacao futura consegue se apoiar em contratos claros;
- regras centrais deixam de ficar implicitas em arquivos monoliticos.

### Dependencias

- Fase 0 concluida.

---

## Fase 2. Extracao do Nucleo Puro de Risco, Portfolio e Estrategia

### Objetivo

Retirar do legado tudo que pode e deve virar dominio puro.

### Escopo

- extrair calculos puros de:
  - health factor
  - drawdown
  - sizing
  - reserve policy
  - leverage constraints
  - portfolio valuation
  - regime classification
- refatorar estrategias para trabalharem sobre estado imutavel ou quase-imutavel;
- transformar decisao de estrategia em saida declarativa, sem side effects diretos;
- isolar LLM como plugin opcional fora da regra principal.

### Entregaveis

- modulo `domain/risk`;
- modulo `domain/portfolio`;
- modulo `domain/strategies`;
- testes unitarios puros por caso de negocio;
- comparacao entre resultado do legado e resultado novo para cenarios-chave.

### Criterios de saida

- motor de decisao testavel sem banco, sem API e sem websocket;
- estrategias principais reproduziveis e deterministicas.

### Riscos

- carregar acoplamentos do legado para o novo dominio;
- esconder side effects em objetos utilitarios.

### Notas importantes

- `AccumulatorStrategy` e `BTCLiteStrategy` sao candidatas prioritarias.
- LLM deve ser rebaixado para papel consultivo:
  - modo `advisory`
  - comparacao offline
  - experimento isolado

---

## Fase 3. Reescrita dos Casos de Uso da Aplicacao

### Objetivo

Parar de usar `api.py` e `system_runner.py` como orquestradores centrais.

### Escopo

Criar casos de uso explicitos:

- `sync_market_data`
- `prepare_features`
- `train_model`
- `generate_predictions`
- `run_backtest`
- `summarize_backtest`
- `run_paper_trading`
- `get_control_center_snapshot`

Cada caso de uso deve:

- receber contratos claros;
- depender de interfaces abstratas;
- devolver resultados estruturados;
- nao conhecer FastAPI.

### Entregaveis

- pasta `application/commands`;
- pasta `application/queries`;
- services de orquestracao desacoplados da web;
- DTOs de request/response internos.

### Criterios de saida

- fluxo principal rodando por casos de uso;
- endpoints antigos podem virar simples wrappers.

### Dependencias

- Fase 2 concluida ao menos para os fluxos centrais.

---

## Fase 4. Nova Camada de Persistencia e Integracao Externa

### Objetivo

Substituir acesso espalhado ao banco e aos provedores por adaptadores consistentes.

### Escopo

#### Banco

- separar leitura analitica de escrita transacional;
- criar repositories claros para:
  - market data
  - predictions
  - trades
  - simulation summaries
  - paper trading events
- introduzir migrations formais;
- revisar naming e ownership das tabelas.

#### Provedores externos

- encapsular integracoes:
  - Binance
  - Blockchair
  - Fear & Greed
  - Deribit
  - TheGraph
  - RPC nodes
  - LLM providers
- padronizar:
  - timeouts
  - retries
  - erro tipado
  - logging
  - observabilidade

### Entregaveis

- adapters e gateways por provedor;
- repositories com interface estavel;
- migrations iniciais;
- testes de integracao reais e isolados;
- politicas de erro e retry documentadas.

### Criterios de saida

- nenhuma regra de negocio acessa banco diretamente;
- nenhuma rota HTTP chama `pandas.read_sql` diretamente;
- provedores externos deixam de vazar para o dominio.

### Decisoes tecnicas recomendadas

- preferir `SQLAlchemy Core` ou camada similar leve, nao ORM pesado por padrao;
- manter `psycopg2` apenas se ficar encapsulado em repositories bem definidos;
- separar conexao de leitura e escrita se necessario depois.

---

## Fase 5. Reescrita da API e dos WebSockets

### Objetivo

Transformar a API numa casca fina.

### Escopo

- quebrar `api.py` em rotas modulares:
  - system
  - market
  - model
  - simulation
  - control_center
  - paper_trading
- remover regra de negocio da camada web;
- tirar mocks de producao dos webSockets centrais;
- revisar startup hooks para nao disparar comportamentos pesados sem controle;
- padronizar schemas de entrada e saida.

### Entregaveis

- `interfaces/api/routes/*.py`;
- `interfaces/api/schemas/*.py`;
- camada de dependencia/injecao;
- contratos HTTP versionados;
- endpoints de health e observabilidade limpos.

### Criterios de saida

- `api.py` deixa de ser arquivo monolitico;
- uma rota so chama um caso de uso e formata resposta;
- websocket de ticker/log fica claramente marcado como:
  - real
  - mock
  - disabled

### Riscos

- quebrar frontend por mudanca de payload;
- manter endpoints antigos indefinidamente.

---

## Fase 6. Reconciliacao do Frontend e do BFF

### Objetivo

Alinhar o Control Center ao backend real e reduzir ruido arquitetural.

### Escopo

- assumir oficialmente `Next.js` como frontend unico;
- remover rastros de arquitetura antiga;
- revisar proxies/BFF internos;
- alinhar rotas de sistema, indicadores, logs, sandbox e dashboard;
- definir claramente o que e:
  - dado real
  - dado derivado
  - placeholder temporario
- fechar fluxos incompletos:
  - login
  - dashboard
  - pulse
  - sandbox

### Entregaveis

- frontend com contratos consistentes;
- remocao de placeholders que fingem comportamento produtivo;
- documentacao atualizada do frontend;
- limpeza de duplicidades e restos de stack anterior.

### Criterios de saida

- frontend e backend falam o mesmo idioma;
- nenhum modulo principal depende de endpoint improvisado ou mock oculto.

---

## Fase 7. Reforma da Estrategia de Testes

### Objetivo

Criar uma malha de testes confiavel para sustentar a migracao.

### Escopo

- separar testes em camadas:
  - unitarios puros
  - integracao com banco
  - integracao com provedores mockados
  - smoke e2e de API
- eliminar dependencia do banco principal nos testes;
- definir factories e fixtures deterministicas;
- criar dataset sintetico pequeno para regressao;
- criar cenarios de ouro para backtest e portfolio.

### Entregaveis

- novo `conftest.py` sem copiar dados da base principal;
- datasets de fixture controlados;
- suite minima de regressao para:
  - treino
  - predicoes
  - simulacao
  - summaries
  - control center

### Criterios de saida

- rodar testes localmente nao exige contaminar banco principal;
- regressao funcional fica mensuravel;
- refatoracao deixa de ser tiro no escuro.

### Qualidade minima recomendada

- unit tests para dominio puro;
- integracao para repositories;
- smoke tests para endpoints criticos;
- coverage focada nos modulos reescritos.

---

## Fase 8. Paper Trading, Runtime Operacional e Limite entre Simulacao e Execucao

### Objetivo

Separar de vez o que e laboratorio, o que e paper trading e o que seria execucao real.

### Escopo

- definir runtime de paper trading como produto separado do backtest;
- criar ingestao real-time controlada para paper trading;
- registrar eventos, ordens simuladas, fills simulados e snapshots;
- revisar kill switch, health checks e alertas;
- definir a fronteira de um executor futuro.

### Entregaveis

- servico claro de paper trading;
- modelo de eventos e auditoria;
- contratos de runtime;
- checklist de readiness para execucao real.

### Criterios de saida

- backtest e paper trading deixam de compartilhar fluxo de forma confusa;
- o produto passa a ter trilha de evolucao operacional coerente.

### Observacao

Se em algum momento houver necessidade real de um executor altamente concorrente e isolado, esta sera a fase para avaliar extrair um servico em `Go`. Nao antes.

---

## Fase 9. Cutover, Limpeza e Aposentadoria do Legado

### Objetivo

Trocar os pontos de entrada e remover o que ficou obsoleto.

### Escopo

- mover rotas para nova pilha;
- remover adaptadores temporarios;
- apagar duplicidades;
- reescrever docs centrais;
- atualizar docker, scripts e fluxo de desenvolvimento;
- registrar decisao final de arquitetura.

### Entregaveis

- backend principal servindo pela nova arquitetura;
- legado desativado ou removido;
- README, docs e ambiente alinhados;
- plano de manutencao pos-migracao.

### Criterios de saida

- operacao principal nao depende mais dos arquivos monoliticos antigos;
- o time consegue evoluir o sistema sem medo de tocar em um “centro nervoso” unico.

## 9. Ordem Recomendada de Execucao

Sequencia recomendada:

1. Fase 0
2. Fase 1
3. Fase 2
4. Fase 3
5. Fase 7 em paralelo parcial com Fases 2 e 3
6. Fase 4
7. Fase 5
8. Fase 6
9. Fase 8
10. Fase 9

Motivo:

- sem contratos, a refatoracao vira remendo;
- sem dominio puro, a API nova so reorganiza bagunca;
- sem testes, a migracao nao e segura;
- sem persistencia reestruturada, continua alto o acoplamento;
- frontend deve vir depois que o backend estabilizar contratos.

## 10. Workstreams Paralelos

Alguns trilhos podem rodar em paralelo.

### Trilha A. Dominio

- portfolio
- risk
- strategy decisions
- regime
- backtest math

### Trilha B. Dados e Persistencia

- repositories
- migrations
- adaptadores de providers
- consolidacao de schemas

### Trilha C. API e Frontend

- modularizacao da API
- schemas
- BFF/proxies
- limpeza do Control Center

### Trilha D. Testes e Qualidade

- fixtures sinteticas
- test matrix
- regressao funcional
- validacoes de contrato

## 11. Marcos de Paridade

Os marcos de paridade impedem que a reescrita fique subjetiva.

### Marco P1. Paridade de Dominio

- mesmo calculo de risco e sizing para cenarios chave;
- mesma classificacao de regime para dataset de referencia;
- mesmas decisoes de estrategia para cenarios congelados.

### Marco P2. Paridade de Backtest

- resultados equivalentes dentro de tolerancia definida;
- ROI, drawdown, numero de trades e equity final dentro de banda aceitavel;
- divergencias explicadas por bug fix ou definicao nova.

### Marco P3. Paridade de API

- frontend consegue consumir a nova API sem gambiarra;
- endpoints criticos entregam payloads previsiveis;
- webSockets e logs com semantica clara.

### Marco P4. Paridade Operacional

- sync, treino, simulacao e dashboard funcionam ponta a ponta;
- ambientes `test`, `paper` e principal isolados corretamente.

## 12. Definicao de Pronto por Fase

Uma fase so fecha quando cumprir:

- codigo implementado;
- testes correspondentes;
- documentacao de decisao;
- observabilidade minima;
- sem regressao critica aberta.

## 13. Riscos Principais e Mitigacoes

### Risco 1. Reescrever demais sem validar

Mitigacao:

- sempre usar marcos de paridade;
- migrar por caso de uso, nao por entusiasmo.

### Risco 2. Levar bugs conceituais do legado para a nova base

Mitigacao:

- separar “paridade” de “reproducao cega”;
- registrar onde a nova implementacao corrige comportamento ruim.

### Risco 3. Quebrar a operacao atual durante a transicao

Mitigacao:

- manter adaptadores temporarios;
- usar feature flags ou rotas paralelas;
- executar cutover apenas quando houver smoke test e rollback.

### Risco 4. Testes continuarem pouco confiaveis

Mitigacao:

- atacar Fase 7 cedo;
- eliminar dependencia do banco principal.

### Risco 5. Frontend continuar consumindo mock disfarçado de real

Mitigacao:

- marcar explicitamente origens de dados;
- remover placeholders silenciosos dos modulos principais.

## 14. Politica para LLM

Decisao recomendada:

- nao usar LLM como fonte primaria de decisao no hot path do backtest ou runtime principal;
- manter LLM apenas em um destes papeis:
  - advisory
  - analise offline
  - explicacao de sinais
  - comparacao experimental

Se o sistema precisar de decisao automatizada em producao, ela deve ser suportada por regras deterministicas, thresholds calibrados e trilha de auditoria reproduzivel.

## 15. Politica para Dados e Testes

Decisoes recomendadas:

- proibir testes dependentes do banco principal;
- usar fixture dataset versionado para regressao;
- definir dataset “golden” pequeno e estavel;
- separar completamente:
  - teste unitario
  - integracao local
  - benchmark quantitativo

## 16. Politica para Configuracao e Ambientes

Objetivos:

- reduzir variavel global espalhada;
- centralizar configuracao por ambiente;
- tornar explicito o que e permitido em:
  - local
  - test
  - paper
  - production

Regras:

- startup nao deve executar tarefas pesadas por default sem configuracao explicita;
- ambientes sensiveis devem ter prechecks obrigatorios;
- segredos nao entram em logs nem fixtures.

## 17. Roadmap Sugerido em Sprints

Estimativa inicial, sujeita a revisao:

- Sprint 1: Fase 0 + Fase 1
- Sprint 2: Fase 2 parcial
- Sprint 3: Fase 2 restante + Fase 7 parcial
- Sprint 4: Fase 3
- Sprint 5: Fase 4 parcial
- Sprint 6: Fase 4 restante + Fase 5 parcial
- Sprint 7: Fase 5 restante + Fase 6
- Sprint 8: Fase 7 fechamento + Fase 8 preparacao
- Sprint 9: Fase 8 + Fase 9

Isto nao e cronograma fixo. E apenas uma ordem pragmatica para reduzir risco.

## 18. Primeiro Corte Recomendado

Se for preciso escolher um ponto de partida concreto, a sequencia mais segura e:

1. definir contratos de `PortfolioState`, `StrategyDecision`, `RiskSnapshot`, `BacktestResult`;
2. extrair `risk_manager` e calculos de portfolio para dominio puro;
3. extrair `AccumulatorStrategy` para versao pura sem side effects;
4. criar `run_backtest` como caso de uso novo;
5. plugar a API antiga nesse caso de uso novo;
6. so depois mexer no restante.

## 19. Resultado Esperado

Ao fim desta reescrita parcial guiada, o DefiSys deve deixar de ser um conjunto de componentes promissores, porem acoplados, e passar a ser uma plataforma com:

- arquitetura legivel;
- dominio central confiavel;
- fluxos separados por responsabilidade;
- testes que sustentam mudanca;
- frontend alinhado ao backend real;
- caminho realista para paper trading e, no futuro, execucao controlada.

## 20. Proximo Passo Imediato

O proximo passo pratico recomendado apos este documento e abrir a Fase 0 em um artefato de execucao, quebrando-a em tarefas operacionais pequenas:

- inventario de endpoints;
- inventario de tabelas;
- mapa de dependencias do backend;
- lista de invariantes de negocio;
- baseline minima de testes e regressao.
