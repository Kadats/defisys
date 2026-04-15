# Fase 1: Contratos de Dominio e Modelo de Sistema

## 1. Proposito

Este documento operacionaliza a Fase 1 definida em [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md).

Objetivo da fase:

- definir a linguagem comum do sistema;
- transformar conhecimento implicito do legado em contratos explicitos;
- separar dominio, aplicacao, infraestrutura e interface de forma clara;
- preparar o terreno para extracao do nucleo puro na Fase 2.

Ao final desta fase, o projeto deve ter contratos suficientes para permitir implementacao nova sem depender da forma atual dos arquivos monoliticos.

## 2. Resultado Esperado

Ao concluir a Fase 1, devemos ter:

- glossario canonico do dominio;
- modelo do sistema com fronteiras de camada;
- contratos de dominio para entidades e value objects principais;
- contratos de entrada e saida dos casos de uso centrais;
- definicao do papel formal do LLM no pipeline de decisao;
- lista de invariantes anexada a cada contrato relevante;
- mapeamento entre contratos novos e estruturas atuais do legado;
- confirmacao de que a stack oficial de interface ja esta congelada:
  - frontend canonico = `Next.js`
  - divergencias de docs/comandos tratadas como debt e nao como ambiguidade arquitetural
- baseline inicial de testes de dominio a ser implementada na Fase 2.

## 3. Regras da Fase

- Ainda nao reescrever o motor inteiro nem trocar a API por completo.
- Evitar mudar comportamento do sistema nesta fase, exceto ajustes minimos para preparar a extracao posterior.
- Toda definicao nova precisa ter correspondencia clara com a realidade mapeada na Fase 0.
- Nenhum contrato deve importar detalhe acidental de banco, FastAPI, `pandas.read_sql` ou websocket.
- O LLM deve continuar no modelo de sistema como componente estrategico, com envelope formal.
- A definicao do frontend oficial nao fica em aberto nesta fase: ela ja deve ser herdada da Fase 0.

## 4. Escopo

Incluido nesta fase:

- definicao das entidades e value objects principais;
- definicao dos DTOs centrais de casos de uso;
- definicao das fronteiras entre `domain`, `application`, `infrastructure` e `interfaces`;
- definicao do contrato do LLM e do fallback heuristico;
- definicao do contrato de resultados de simulacao e dashboard snapshot;
- definicao da primeira malha de testes de dominio.

Fora do escopo desta fase:

- migracao de rotas HTTP;
- reescrita de repositories concretos;
- reescrita do `TradingEngine`;
- troca de schema ou migracao de banco;
- redesign do frontend.

## 5. Dependencias de Entrada

Esta fase parte diretamente dos artefatos da Fase 0:

- [phase-0-endpoints.md](/home/luckstyle/repo/private/defisys-v1/phase-0-endpoints.md)
- [phase-0-data-map.md](/home/luckstyle/repo/private/defisys-v1/phase-0-data-map.md)
- [phase-0-flows.md](/home/luckstyle/repo/private/defisys-v1/phase-0-flows.md)
- [phase-0-invariants.md](/home/luckstyle/repo/private/defisys-v1/phase-0-invariants.md)
- [phase-0-tests.md](/home/luckstyle/repo/private/defisys-v1/phase-0-tests.md)
- [phase-0-risks.md](/home/luckstyle/repo/private/defisys-v1/phase-0-risks.md)

## 6. Workstreams

### WS1. Glossario e Modelo Conceitual

Definir:

- termos canonicos do dominio;
- conceitos que hoje aparecem com nomes diferentes no legado;
- diferenca entre dado bruto, feature, predicao, decisao e execucao simulada.

### WS2. Contratos de Dominio

Modelar entidades e value objects principais:

- `MarketCandle`
- `FeatureVector`
- `Prediction`
- `PortfolioState`
- `Position`
- `TradeRecord`
- `RiskSnapshot`
- `StrategyDecision`
- `BacktestResult`
- `SimulationSummary`

### WS3. Casos de Uso e DTOs

Definir contratos de entrada e saida para:

- `sync_market_data`
- `prepare_features`
- `train_model`
- `generate_predictions`
- `run_backtest`
- `build_dashboard_snapshot`

### WS4. Contrato do LLM

Definir formalmente:

- contexto minimo que entra;
- formato aceito de resposta;
- acoes permitidas;
- envelope de validacao;
- politica de fallback;
- logging e rastreabilidade;
- campos necessarios para avaliacao offline.

### WS5. Fronteiras de Camada

Deixar explicito:

- o que pertence ao `domain`;
- o que pertence ao `application`;
- o que e responsabilidade de `infrastructure`;
- o que fica restrito a `interfaces`.

### WS6. Baseline de Testes de Dominio

Definir:

- testes puros que a Fase 2 precisa implementar primeiro;
- cenarios de ouro ligados aos contratos;
- quais invariantes precisam virar asserts automatizados.

## 7. Entregaveis da Fase

Arquivos esperados ao final da Fase 1:

- `phase-1.md`
- `phase-1-domain-glossary.md`
- `phase-1-system-model.md`
- `phase-1-domain-contracts.md`
- `phase-1-use-cases.md`
- `phase-1-llm-contract.md`
- `phase-1-test-baseline.md`

Se algum desses artefatos for consolidado em outro formato, isso deve ser registrado aqui.

## 8. Decisoes Estruturais Que a Fase Precisa Fechar

### 8.1 O que e entidade, value object e DTO

Precisamos sair desta fase sem ambiguidade sobre:

- o que carrega identidade de negocio;
- o que e apenas composicao imutavel de dados;
- o que e payload de caso de uso;
- o que e view model de interface.

### 8.2 Onde termina a predicao e onde comeca a decisao

O contrato novo precisa separar claramente:

- predicao de ML;
- leitura de regime;
- snapshot de risco;
- consulta ao LLM;
- decisao final da estrategia/policy layer.

### 8.3 Qual e a unidade canonica do resultado de simulacao

Precisamos definir:

- diferenca entre `BacktestResult` e `SimulationSummary`;
- o que e runtime/report detalhado;
- o que e resumo oficial persistivel;
- o que e snapshot pronto para dashboard.

### 8.4 Como o LLM entra sem contaminar o dominio

Precisamos deixar claro:

- o LLM nao vira entidade de dominio;
- ele entra por porta/contrato;
- a decisao validada e que entra no dominio;
- fallback heuristico precisa respeitar a mesma interface.

## 9. Checklist Operacional

### 9.1 Glossario do Dominio

- [x] Definir nomes canonicos para conceitos centrais.
- [x] Registrar sinonimos e termos legados que devem ser aposentados.
- [x] Separar claramente market data, features, predictions, decisions e execution.
- [x] Registrar conceitos que sao de produto e conceitos que sao apenas de implementacao.

### 9.2 Modelo de Sistema

- [x] Descrever as quatro camadas alvo:
  - domain
  - application
  - infrastructure
  - interfaces
- [x] Registrar exemplos concretos do que deve sair de `api.py`.
- [x] Registrar exemplos concretos do que deve sair de `system_runner.py`.
- [x] Registrar onde entram dashboard, BFF, websocket e CLI.

### 9.3 Contratos de Dominio

- [x] Definir contrato de `MarketCandle`.
- [x] Definir contrato de `FeatureVector`.
- [x] Definir contrato de `Prediction`.
- [x] Definir contrato de `PortfolioState`.
- [x] Definir contrato de `Position`.
- [x] Definir contrato de `TradeRecord`.
- [x] Definir contrato de `RiskSnapshot`.
- [x] Definir contrato de `StrategyDecision`.
- [x] Definir contrato de `BacktestResult`.
- [x] Definir contrato de `SimulationSummary`.

### 9.4 Invariantes por Contrato

- [x] Anexar invariantes quantitativas aos contratos certos.
- [x] Anexar invariantes de risco aos contratos certos.
- [x] Anexar invariantes operacionais aos contratos certos.
- [x] Anexar invariantes do LLM aos contratos certos.
- [x] Confirmar que nenhum contrato novo viola zero look-ahead.

### 9.5 Casos de Uso e DTOs

- [x] Definir input/output de `sync_market_data`.
- [x] Definir input/output de `prepare_features`.
- [x] Definir input/output de `train_model`.
- [x] Definir input/output de `generate_predictions`.
- [x] Definir input/output de `run_backtest`.
- [x] Definir input/output de `build_dashboard_snapshot`.
- [x] Separar DTO de comando, DTO de consulta e DTO de resposta.

### 9.6 Contrato do LLM

- [x] Definir `RiskDecisionContext` canonico.
- [x] Definir `LLMDecisionResponse` canonico.
- [x] Definir conjunto finito de acoes aceitas.
- [x] Definir validacao estrutural da resposta.
- [x] Definir fallback heuristico compativel com o mesmo contrato.
- [x] Definir campos minimos para auditoria e avaliacao offline.

### 9.7 Mapeamento de Legado

- [x] Mapear `api.py` para contratos novos.
- [x] Mapear `system_runner.py` para casos de uso novos.
- [x] Mapear `accumulator.py` para contratos de decisao, risco e portfolio.
- [x] Mapear `trading_data.py` para contratos de trade e summary.
- [x] Registrar o que fica no legado temporariamente.

### 9.8 Baseline de Testes

- [x] Listar testes puros que a Fase 2 deve implementar primeiro.
- [x] Registrar golden scenarios ligados a contratos, nao a arquivos legados.
- [x] Definir quais invariantes devem virar testes obrigatorios.
- [x] Definir o gate minimo para considerar a extracao segura.

### 9.9 Fechamento

- [x] Consolidar aprendizados em artefatos da fase.
- [x] Confirmar que os contratos permitem iniciar a Fase 2.
- [x] Registrar pontos em aberto que precisam de decisao futura.
- [x] Declarar o primeiro corte tecnico recomendado para implementacao.

## 10. Artefatos Alvo

## 10.1 `phase-1-domain-glossary.md`

Deve conter:

- termos canonicos;
- termos legados;
- definicoes curtas;
- conflitos de nomenclatura resolvidos.

## 10.2 `phase-1-system-model.md`

Deve conter:

- desenho conceitual das camadas;
- responsabilidades permitidas por camada;
- fluxos principais mapeados para a arquitetura alvo.

## 10.3 `phase-1-domain-contracts.md`

Deve conter:

- entidades;
- value objects;
- campos obrigatorios;
- invariantes por contrato;
- observacoes de migracao.

## 10.4 `phase-1-use-cases.md`

Deve conter:

- lista de casos de uso;
- input/output de cada um;
- dependencias abstratas esperadas;
- relacao com endpoints legados.

## 10.5 `phase-1-llm-contract.md`

Deve conter:

- contexto de entrada do LLM;
- resposta aceita;
- validadores;
- fallback;
- observabilidade;
- estrategia de avaliacao.

## 10.6 `phase-1-test-baseline.md`

Deve conter:

- testes minimos da Fase 2;
- cenarios de ouro;
- gates de regressao de dominio.

## 11. Perguntas que a Fase Precisa Responder

1. Qual e a linguagem canonica do sistema a partir de agora?
2. Que partes do legado representam dominio real e que partes sao so acoplamento acidental?
3. Onde termina ML e onde comeca policy/strategy?
4. Como preservar o edge do LLM sem espalhar dependencia informal pelo codigo?
5. Que contratos precisam de paridade exata e quais podem melhorar sem risco de produto?
6. Qual o menor conjunto de contratos que destrava a Fase 2?

## 12. Criterios de Saida

A Fase 1 so fecha quando:

- o vocabulario do sistema estiver estabilizado;
- as fronteiras de camada estiverem descritas;
- os contratos centrais do dominio estiverem definidos;
- os casos de uso principais estiverem com input/output claros;
- o papel do LLM estiver formalizado;
- houver baseline clara de testes para a extracao do nucleo puro.

## 13. Dependencias para a Fase 2

A Fase 2 depende diretamente desta fase para:

- extrair risco, portfolio e decisao para codigo puro;
- evitar copiar acoplamentos do legado;
- escrever testes contra contratos, e nao contra implementacoes monoliticas;
- iniciar implementacao nova com pouca ambiguidade.

## 14. Status

Estado atual da fase:

- Status: `planned`
- Dono atual: `Codex + usuário`
- Documento mestre relacionado: [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md)

## 15. Proximo Passo Imediato

Material produzido na Fase 1:

1. `phase-1-domain-glossary.md`
2. `phase-1-system-model.md`
3. `phase-1-domain-contracts.md`
4. `phase-1-use-cases.md`
5. `phase-1-llm-contract.md`
6. `phase-1-test-baseline.md`

Entrada recomendada para a Fase 2:

1. extrair `RiskSnapshot`, `PortfolioState` e `StrategyDecision` para codigo puro;
2. criar os primeiros DTOs de `run_backtest` e `build_dashboard_snapshot`;
3. isolar o contrato do LLM atras de uma porta unica;
4. escrever a baseline inicial de testes unitarios desses contratos antes de migrar mais comportamento.

## 16. Observacao Operacional

Este documento registra o planejamento consolidado da fase, nao evidencia de que a fase ja foi executada no codigo.
