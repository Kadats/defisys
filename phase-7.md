# Fase 7: Reforma da Estrategia de Testes

## 1. Proposito

Este documento operacionaliza a Fase 7 definida em [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md).

Objetivo da fase:

- criar uma malha de testes confiavel para sustentar a migracao;
- separar testes por camada e finalidade;
- eliminar dependencia do banco principal;
- transformar a regressao funcional em algo mensuravel e repetivel;
- permitir execucao antecipada da trilha de testes do nucleo sem bloquear nos smoke tests de interface;
- reduzir a chance de a reescrita ficar “verde no mock e quebrada no real”.

Ao final desta fase, o projeto deve ter uma estrategia de testes coerente com a nova arquitetura e segura para apoiar execucao das fases seguintes.

## 2. Resultado Esperado

Ao concluir a Fase 7, devemos ter:

- dois trilhos bem separados:
  - `Fase 7A`
    - novo desenho de `conftest.py` sem copiar dados da base principal
    - unitario puro
    - integracao com banco
    - integracao com gateways mockados ou fakes controlados
    - fixtures e datasets sinteticos controlados
    - baseline minima de regressao para treino, predicao, simulacao, summaries e control center
  - `Fase 7B`
    - smoke de API
    - smoke de BFF
    - smoke de frontend quando fizer sentido
    - smoke de WebSockets centrais
- gates objetivos para validar as fases reescritas sem confundir baseline de nucleo com smoke de interface.

## 3. Regras da Fase

- Esta fase esta aberta apenas como planejamento.
- Nenhuma implementacao de codigo desta fase deve comecar sem autorizacao explicita do usuario.
- Nenhum teste deve depender da base principal para preparar ambiente.
- Teste unitario nao deve conhecer banco, FastAPI, WebSocket ou arquivo real sem necessidade.
- Integracao deve ser explicita e isolada.
- Mock nao pode substituir completamente a validacao dos contratos centrais.
- A suite precisa refletir a arquitetura alvo, nao reforcar o monolito legado.

## 3.1 Gate de Execucao

Antes de executar a Fase 7 no codigo, precisamos ter:

- para `Fase 7A`:
  - contratos das Fases 0 e 1 definidos;
  - entendimento claro das camadas alvo de dominio, aplicacao, infraestrutura e interfaces;
  - acordo sobre quais fluxos precisam de regressao obrigatoria;
  - confirmacao explicita do usuario para iniciar execucao;
- para `Fase 7B`:
  - Fases 5 e 6 suficientemente estabilizadas nos contratos de interface;
  - smoke tests claramente separados da regressao funcional profunda;
  - confirmacao explicita do usuario para iniciar execucao.

## 4. Escopo

Incluido nesta fase:

- redesenho da estrategia de testes;
- separacao da suite por camada;
- redesign de fixtures e `conftest.py`;
- definicao de datasets sinteticos e cenarios de ouro;
- definicao da baseline de regressao por fluxo;
- plano de smoke tests da API e do frontend/BFF;
- revisao do papel de mocks, fakes e testes de integracao.

Estruturacao obrigatoria da fase:

- `Fase 7A`
  - taxonomia da suite
  - fixtures e ambiente
  - datasets sinteticos
  - baseline de regressao
  - papel de mocks, fakes e integracao
- `Fase 7B`
  - smoke de API
  - smoke de BFF
  - smoke de frontend
  - smoke de WebSockets

Fora do escopo desta fase:

- aumento cego de coverage como fim em si;
- benchmark quantitativo de estrategia em profundidade;
- execucao real de infraestrutura externa;
- redesign do produto;
- substituicao das fases de dominio/aplicacao pela suite de testes.

## 5. Dependencias de Entrada

Esta fase depende diretamente de:

- [phase-0-tests.md](/home/luckstyle/repo/private/defisys-v1/phase-0-tests.md)
- [phase-0-risks.md](/home/luckstyle/repo/private/defisys-v1/phase-0-risks.md)
- [phase-1-domain-contracts.md](/home/luckstyle/repo/private/defisys-v1/phase-1-domain-contracts.md)
- [phase-1-use-cases.md](/home/luckstyle/repo/private/defisys-v1/phase-1-use-cases.md)

Dependencias especificas por trilha:

- `Fase 7A`
  - [phase-2.md](/home/luckstyle/repo/private/defisys-v1/phase-2.md) para testes de dominio puro
  - [phase-3.md](/home/luckstyle/repo/private/defisys-v1/phase-3.md) para baseline de casos de uso
- `Fase 7B`
  - [phase-5.md](/home/luckstyle/repo/private/defisys-v1/phase-5.md)
  - [phase-6.md](/home/luckstyle/repo/private/defisys-v1/phase-6.md)

## 6. Workstreams

### WS1. Taxonomia da Suite

Definir a estrutura alvo da suite:

- testes unitarios de dominio;
- testes unitarios de aplicacao;
- testes de integracao de repositories;
- testes de integracao de gateways;
- smoke tests de API;
- smoke tests de frontend/BFF;
- testes especiais do envelope do LLM.

### WS2. Fixtures e Ambiente

Planejar:

- novo `conftest.py`;
- fixtures deterministicas;
- ambientes isolados;
- estrategia de banco de teste;
- teardown e limpeza previsiveis.

### WS3. Datasets Sinteticos

Definir:

- dataset pequeno para mercado e features;
- dataset pequeno para predicoes;
- cenarios de ouro de simulacao;
- snapshots de portfolio e risco;
- datasets especificos para o envelope do LLM quando necessario.

### WS4. Baseline de Regressao

Definir a regressao minima obrigatoria para:

- treino;
- predicoes;
- simulacao/backtest;
- summaries;
- control center;
- frontend/BFF reconciliado.

### WS5. Estrategia de Mock, Fake e Integracao

Definir:

- quando usar mock;
- quando usar fake;
- quando usar integracao real com DB;
- quando usar smoke de interface;
- o que nao pode mais ser validado so com patching.

### WS6. Gates por Fase

Definir:

- qual baseline a Fase 2 precisa passar;
- qual baseline da `Fase 7A` destrava Fase 3 e Fase 4;
- qual baseline a Fase 5 precisa passar;
- qual baseline a Fase 6 precisa passar;
- qual baseline da `Fase 7B` destrava Fase 8;
- quais testes destravam a Fase 8 e a Fase 9.

## 7. Entregaveis da Fase

Arquivos esperados ao final da Fase 7:

- `phase-7.md`
- `phase-7-test-taxonomy.md`
- `phase-7-fixtures-plan.md`
- `phase-7-regression-baseline.md`
- `phase-7-smoke-plan.md`

Classificacao recomendada dos artefatos:

- `Fase 7A`
  - `phase-7-test-taxonomy.md`
  - `phase-7-fixtures-plan.md`
  - `phase-7-regression-baseline.md`
- `Fase 7B`
  - `phase-7-smoke-plan.md`

Entregaveis de codigo esperados quando houver execucao:

- novo `tests/conftest.py`;
- fixtures e datasets sinteticos controlados;
- reorganizacao da suite por camada;
- smoke tests minimos da API e do frontend/BFF.

## 8. Decisoes Tecnicas Recomendadas

- separar a suite por tipo e risco, nao so por arquivo historico;
- preservar testes valiosos de dominio e risco, mas reduzir acoplamento a detalhes de implementacao;
- tratar `conftest.py` atual como debt critico a ser substituido;
- criar datasets pequenos e deterministas;
- priorizar regressao funcional de fluxos centrais sobre coverage cosmetica;
- permitir que `Fase 7A` comece cedo, sem esperar a reconciliacao completa da interface;
- manter testes do LLM focados em contrato, fallback, validacao e seguranca.

## 9. Checklist Operacional

### 9.1 Taxonomia

- [ ] Definir categorias oficiais da suite.
- [ ] Mapear testes atuais para a nova taxonomia.
- [ ] Registrar testes que valem ser preservados.
- [ ] Registrar testes que devem ser reescritos ou aposentados.

### 9.2 Fixtures e Ambiente

- [ ] Definir substituto do `conftest.py` atual.
- [ ] Definir estrategia de isolamento do banco de teste.
- [ ] Definir fixtures deterministicas.
- [ ] Definir politica de setup e teardown.

### 9.3 Datasets

- [ ] Definir dataset sintetico de mercado.
- [ ] Definir dataset sintetico de predicoes.
- [ ] Definir cenarios de ouro de portfolio e risco.
- [ ] Definir cenarios de ouro de simulacao.

### 9.4 Baseline de Regressao

- [ ] Definir baseline minima de treino.
- [ ] Definir baseline minima de predicoes.
- [ ] Definir baseline minima de simulacao.
- [ ] Definir baseline minima de summaries.
- [ ] Definir baseline minima de control center.

### 9.5 Smoke e Interfaces

- [ ] Definir smoke tests da API.
- [ ] Definir smoke tests do BFF.
- [ ] Definir smoke tests do frontend quando fizer sentido.
- [ ] Definir smoke dos WebSockets centrais.

### 9.6 Mocks e Integracao

- [ ] Definir quando mock e aceitavel.
- [ ] Definir quando integracao real e obrigatoria.
- [ ] Definir fakes controlados por camada.
- [ ] Definir o que nao pode mais ser validado so com patch.

### 9.7 Fechamento

- [ ] Consolidar aprendizados em artefatos da fase.
- [ ] Confirmar que a regressao minima ficou mensuravel.
- [ ] Confirmar que testes locais nao dependem da base principal.
- [ ] Declarar o corte minimo que destrava as proximas fases executaveis.

## 10. Primeiro Corte Tecnico Recomendado

Sequencia recomendada para a futura execucao:

1. executar `Fase 7A`:
  - substituir a dependencia estrutural do `conftest.py` atual
  - isolar dataset sintetico pequeno para dominio, predicao e simulacao
  - criar a baseline minima para risco, portfolio, predicoes e summary
2. so depois executar `Fase 7B`:
  - adicionar smoke da API nova e do BFF reconciliado
  - adicionar smoke de frontend e WebSocket quando os contratos de interface estiverem estaveis
3. so depois expandir a suite para cobertura mais ampla.

## 11. Perguntas que a Fase Precisa Responder

1. Qual o menor conjunto de testes que realmente torna a reescrita segura?
2. Como substituir o `conftest.py` atual sem perder utilidade da suite?
3. Quais testes atuais protegem regra de negocio e quais so protegem mock?
4. Quais fluxos precisam de cenarios de ouro obrigatorios?
5. Qual o gate minimo por fase para evitar regressao silenciosa?

## 12. Criterios de Saida

A Fase 7 so fecha quando:

- a estrategia nova de testes estiver definida por camadas e por trilhas `7A` e `7B`;
- `conftest.py` atual puder ser substituido por modelo isolado;
- houver baseline minima de regressao para os fluxos criticos do nucleo;
- houver smoke minimo planejado para interfaces reconciliadas;
- a dependencia do banco principal deixar de ser pressuposto da validacao;
- refatoracao futura deixar de depender de “suite verde por patch”.

## 13. Dependencias para a Fase 8

A Fase 8 depende diretamente desta fase para:

- validar paper trading e runtime operacional com baseline confiavel;
- medir diferenca entre simulacao, paper e runtime;
- sustentar migracao sem contaminar ambiente real;
- transformar fluxos operacionais em algo auditavel e verificavel.

## 14. Status

Estado atual da fase:

- Status: `planned`
- Dono atual: `Codex + usuário`
- Documento mestre relacionado: [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md)

## 15. Proximo Passo Imediato

Planejamento da fase consolidado com os seguintes artefatos:

1. `phase-7-test-taxonomy.md`
2. `phase-7-fixtures-plan.md`
3. `phase-7-regression-baseline.md`
4. `phase-7-smoke-plan.md`

Proximo passo recomendado:

1. abrir o planejamento da Fase 8;
2. so depois iniciar execucao da Fase 7 quando houver autorizacao explicita do usuario.

## 16. Observacao Operacional

Este documento e um plano de execucao da fase, nao evidencia de que a fase ja foi executada.
