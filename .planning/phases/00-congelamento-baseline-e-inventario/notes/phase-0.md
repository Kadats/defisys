# Fase 0: Congelamento, Baseline e Inventario

## 1. Proposito

Este documento operacionaliza a Fase 0 definida em [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md).

Objetivo da fase:

- congelar o que importa;
- mapear o que existe de verdade;
- separar comportamento essencial de legado descartavel;
- preparar a base para a Fase 1 sem entrar ainda em refatoracao estrutural.

Ao final desta fase, o projeto deve ter um baseline tecnico claro o bastante para permitir reescrita parcial guiada com risco controlado.

## 2. Resultado Esperado

Ao concluir a Fase 0, devemos ter:

- inventario dos endpoints atuais;
- inventario das tabelas e usos de banco;
- mapa dos fluxos principais do backend;
- lista de invariantes de negocio;
- classificacao dos testes atuais;
- linha de base de regressao minima;
- lista priorizada de riscos e debt tecnico;
- verdade oficial de interface e operacao local registrada:
  - frontend canonico = `frontend/` em `Next.js`
  - `frontend-vue-backup/` e docs/comandos de Vue/Vite tratados como legado
  - comandos oficiais passam a refletir o frontend real
- definicao do que deve permanecer, do que deve migrar e do que pode morrer.

## 3. Regras da Fase

- Nao adicionar features novas no backend critico durante esta fase.
- Nao refatorar arquitetura ainda, exceto pequenos ajustes para suportar observabilidade do inventario.
- Nao apagar comportamento legado sem registrar antes.
- Toda descoberta relevante deve virar artefato neste documento ou em anexos derivados.

## 4. Escopo

Incluido nesta fase:

- backend `api`, `system_runner`, `core`, `ai`, `data`, `services`, `strategies`;
- frontend atual em `frontend/`;
- testes em `tests/`;
- infraestrutura local relevante:
  - `docker-compose.yml`
  - `.env.example`
  - `Makefile`
  - `setup_cloud.sh`

Fora do escopo desta fase:

- redesenho de frontend;
- troca de linguagem;
- reescrita do motor de trading;
- migracao de banco;
- alteracao de estrategia de produto.

## 5. Workstreams

### WS1. Inventario de Interfaces

Mapear tudo que expoe comportamento para fora:

- endpoints HTTP;
- webSockets;
- proxies/BFF do frontend;
- jobs e scripts de operacao;
- pontos de startup automatico.

### WS2. Inventario de Dados

Mapear:

- tabelas;
- ownership por modulo;
- fluxo de leitura/escrita;
- separacao entre ambiente principal, teste e paper;
- dependencias diretas de `psycopg2`, `pandas.read_sql` e SQL solto.

### WS3. Inventario de Fluxos de Negocio

Mapear ponta a ponta:

- sync de dados;
- preparo de features;
- treino do modelo;
- geracao de predicoes;
- simulacao/backtest;
- agregacao de resultados;
- control center.

### WS4. Inventario de Regras e Invariantes

Mapear regras que nao podem se perder:

- no look-ahead;
- reserva de gas;
- health factor;
- drawdown global e diario;
- leverage constraints;
- isolamento de ambientes;
- fallback e seguranca de API keys;
- uso do LLM na decisao.

### WS5. Inventario de Testes e Baseline

Mapear:

- testes realmente uteis;
- testes que so mockam implementacao;
- testes dependentes de banco;
- cobertura funcional minima necessaria para migrar;
- cenarios de ouro para comparar comportamento.

## 6. Entregaveis da Fase

Arquivos esperados ao final da Fase 0:

- `phase-0.md`
- `phase-0-endpoints.md`
- `phase-0-data-map.md`
- `phase-0-flows.md`
- `phase-0-invariants.md`
- `phase-0-tests.md`
- `phase-0-risks.md`

Se algum deles for consolidado em outro formato, isso deve ser registrado aqui.

## 7. Checklist Operacional

### 7.1 Baseline do Sistema

- [x] Registrar status atual do repositório e principais artefatos.
- [x] Confirmar stack real em uso no backend.
- [x] Confirmar stack real em uso no frontend.
- [x] Registrar inconsistencias entre documentacao e implementacao.
- [x] Congelar a verdade oficial do frontend e dos comandos locais.
- [x] Registrar dependencias ausentes ou fragilidade do ambiente local.

### 7.2 Inventario de Interfaces

- [x] Listar todas as rotas FastAPI atuais.
- [x] Classificar rotas por dominio funcional:
  - system
  - market
  - model
  - simulation
  - analytics
  - control center
- [x] Listar webSockets e dizer se sao reais, mockados ou hibridos.
- [x] Listar proxies/BFF do frontend.
- [x] Mapear scripts e pontos de bootstrap automatico.

### 7.3 Inventario de Dados

- [x] Listar tabelas principais usadas hoje.
- [x] Mapear quem grava e quem le cada tabela.
- [x] Identificar tabelas de treino, simulacao, paper e teste.
- [x] Identificar acessos diretos a banco espalhados fora de repositories formais.
- [x] Registrar onde ha dependencia de SQL solto e `pandas.read_sql`.

### 7.4 Inventario de Fluxos

- [x] Descrever fluxo de sync de dados.
- [x] Descrever fluxo de treino do modelo.
- [x] Descrever fluxo de geracao de predicoes.
- [x] Descrever fluxo de simulacao/backtest.
- [x] Descrever fluxo de consolidacao de resultados.
- [x] Descrever fluxo do dashboard/control center.

### 7.5 Invariantes de Negocio

- [x] Capturar invariantes de risco.
- [x] Capturar invariantes de portfolio e tesouraria.
- [x] Capturar invariantes de dados e ML.
- [x] Capturar invariantes operacionais por ambiente.
- [x] Capturar invariantes do pipeline de decisao com LLM.

### 7.6 Testes e Regressao

- [x] Catalogar suite atual por tipo de teste.
- [x] Identificar testes fragilmente acoplados a implementacao.
- [x] Identificar testes dependentes de banco principal.
- [x] Definir baseline minima de regressao funcional.
- [x] Definir cenarios de comparacao para a Fase 1 e Fase 2.

### 7.7 Riscos e Debt

- [x] Listar monolitos principais e seus impactos.
- [x] Listar acoplamentos criticos.
- [x] Listar mocks perigosos em runtime.
- [x] Listar riscos de migracao.
- [x] Priorizar debt tecnico por impacto e urgencia.

### 7.8 Fechamento

- [x] Consolidar aprendizados em artefatos da fase.
- [x] Declarar o que fica, o que migra e o que tende a ser aposentado.
- [x] Registrar recomendacoes de entrada para a Fase 1.
- [x] Confirmar se ja existe material suficiente para abrir contratos de dominio.

## 8. Evidencias a Coletar

Durante a execucao desta fase, coletar evidencias concretas:

- caminhos de arquivo;
- nomes de rotas;
- nomes de tabelas;
- ownership dos modulos;
- contratos de entrada e saida observados;
- exemplos de payloads quando necessario;
- dependencias de ambiente;
- falhas de consistencia entre docs e codigo.

Evitar opiniao vaga sem evidencias.

## 9. Perguntas que a Fase Precisa Responder

1. Quais comportamentos atuais sao de fato essenciais para o produto?
2. Quais partes do sistema sao so experimento, placeholder ou legado arrastado?
3. Onde o dominio esta escondido dentro de infraestrutura ou camada web?
4. Quais regras nao podem mudar durante a reescrita?
5. Quais partes do uso de LLM sao core para o edge do sistema e quais sao acoplamento ruim?
6. O que precisa de paridade exata e o que pode ser corrigido durante a migracao?
7. Qual o menor conjunto de testes e cenarios que torna a reescrita segura?

## 10. Criterios de Saida

A Fase 0 so fecha quando:

- o inventario tecnico estiver suficientemente completo;
- os fluxos principais estiverem descritos;
- os invariantes essenciais estiverem registrados;
- os riscos estiverem priorizados;
- a baseline minima de regressao estiver definida;
- houver insumo concreto para abrir a Fase 1.

## 11. Dependencias para a Fase 1

A Fase 1 depende diretamente desta fase para:

- definir contratos de dominio corretos;
- evitar reescrever em cima de comportamento mal entendido;
- saber o que precisa de paridade e o que pode ser limpo;
- proteger as regras centrais do sistema, inclusive o papel do LLM.

## 12. Status

Estado atual da fase:

- Status: `planned`
- Dono atual: `Codex + usuário`
- Documento mestre relacionado: [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md)

## 13. Proximo Passo Imediato

Material produzido na Fase 0:

1. `phase-0-endpoints.md`
2. `phase-0-data-map.md`
3. `phase-0-flows.md`
4. `phase-0-invariants.md`
5. `phase-0-tests.md`
6. `phase-0-risks.md`

Entrada recomendada para a Fase 1:

1. abrir contratos de dominio para candle, feature vector, prediction, decision, trade e simulation summary;
2. separar commands e queries da superficie HTTP alvo;
3. desenhar casos de uso explicitos para sync, treino, predicao, backtest e dashboard snapshot;
4. definir a primeira baseline executavel de regressao em cima desses contratos.

Decisao oficial congelada ja nesta fase:

- frontend canonico = `frontend/` em `Next.js`;
- referencias a Vue/Vite ficam tratadas como legado documental e estrutural;
- a Fase 6 vai reconciliar contratos e UI, nao decidir novamente qual e a stack oficial.

## 14. Observacao Operacional

Este documento registra o planejamento consolidado da fase, nao evidencia de que a fase ja foi executada no codigo.
