# Fase 2: Extracao do Nucleo Puro de Risco, Portfolio e Estrategia

## 1. Proposito

Este documento operacionaliza a Fase 2 definida em [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md).

Objetivo da fase:

- retirar do legado as regras que ja podem virar dominio puro;
- criar os primeiros modulos reais em `domain`;
- mover a decisao para contratos declarativos e testaveis;
- preparar a aplicacao para a Fase 3 sem depender do comportamento monolitico atual.

Ao final desta fase, o projeto deve ter um nucleo decisorio minimo executavel e testavel sem banco, sem FastAPI e sem websocket.

## 2. Resultado Esperado

Ao concluir a Fase 2, devemos ter:

- modulos iniciais de `domain/risk`, `domain/portfolio` e `domain/strategies`;
- regras puras para health factor, drawdown, sizing e reserve policy;
- `StrategyDecision` produzida sem side effect direto;
- `RiskSnapshot` e `PortfolioState` como contratos implementados, nao apenas documentados;
- integracao do LLM atras de uma porta unica, com fallback compativel;
- baseline inicial de testes unitarios puros rodando sobre o novo dominio;
- comparacao controlada entre cenarios congelados do legado e do novo nucleo.

## 3. Regras da Fase

- Esta fase esta aberta apenas como planejamento.
- Nenhuma implementacao de codigo desta fase deve comecar sem autorizacao explicita do usuario.
- Priorizar extracao de codigo puro antes de criar novos wrappers.
- Nao mover codigo para a nova pasta apenas por organizacao; mover somente quando o comportamento estiver claro.
- Evitar side effects no dominio:
  - sem banco
  - sem logger operacional como dependencia obrigatoria
  - sem chamada externa
- O LLM continua participando da decisao, mas somente por porta/contrato.
- Toda extracao importante deve nascer com teste unitario correspondente.

## 3.1 Gate de Execucao

Antes de executar a Fase 2 no codigo, precisamos ter:

- confirmacao explicita do usuario para sair do modo planejamento;
- definicao do primeiro corte tecnico a ser implementado;
- criterio de validacao objetiva para esse corte;
- rollback claro para as alteracoes iniciais.

## 4. Escopo

Incluido nesta fase:

- extracao de calculos puros de risco;
- extracao de calculos puros de portfolio;
- extracao inicial da logica de decisao das estrategias prioritarias;
- adaptacao do caminho de decisao para retornar `StrategyDecision`;
- criacao da primeira malha de testes puros de dominio;
- comparacao de cenarios-chave entre legado e novo dominio.

Fora do escopo desta fase:

- migracao total da API;
- troca completa do `TradingEngine`;
- reescrita total de repositories;
- redesign de payload HTTP;
- troca de schema de banco.

## 5. Dependencias de Entrada

Esta fase depende diretamente dos artefatos da Fase 1:

- [phase-1-domain-glossary.md](/home/luckstyle/repo/private/defisys-v1/phase-1-domain-glossary.md)
- [phase-1-system-model.md](/home/luckstyle/repo/private/defisys-v1/phase-1-system-model.md)
- [phase-1-domain-contracts.md](/home/luckstyle/repo/private/defisys-v1/phase-1-domain-contracts.md)
- [phase-1-use-cases.md](/home/luckstyle/repo/private/defisys-v1/phase-1-use-cases.md)
- [phase-1-llm-contract.md](/home/luckstyle/repo/private/defisys-v1/phase-1-llm-contract.md)
- [phase-1-test-baseline.md](/home/luckstyle/repo/private/defisys-v1/phase-1-test-baseline.md)

## 6. Workstreams

### WS1. Dominio de Risco

Extrair regras puras para:

- health factor;
- kill switch;
- drawdown global e diario;
- leverage constraints;
- reserve policy;
- health status.

### WS2. Dominio de Portfolio

Extrair regras puras para:

- consolidacao de tesourarias;
- valorizacao de portfolio;
- exposicao liquida;
- consistencia entre caixa, BTC, LP e Aave.

### WS3. Dominio de Decisao e Estrategia

Extrair a parte declarativa da decisao:

- sinal quantitativo;
- contexto de risco;
- contexto de carteira;
- recomendacao do LLM;
- decisao final validada.

### WS4. Porta do LLM

Materializar a fronteira definida na Fase 1:

- entrada `RiskDecisionContext`;
- saida `LLMDecisionResponse`;
- fallback deterministico;
- validacao estrutural unica.

### WS5. Testes Puros de Dominio

Criar a baseline minima para:

- `RiskSnapshot`
- `PortfolioState`
- `StrategyDecision`
- contrato do LLM e fallback

### WS6. Comparacao com o Legado

Congelar cenarios e comparar:

- mesma entrada;
- mesma decisao esperada;
- mesmas protecoes de risco;
- divergencias explicitadas quando forem correcao intencional.

## 7. Entregaveis da Fase

Arquivos esperados ao final da Fase 2:

- `phase-2.md`
- `phase-2-design-notes.md`
- `phase-2-comparison.md`

Entregaveis de codigo esperados:

- pasta `backend/src/domain/risk/`
- pasta `backend/src/domain/portfolio/`
- pasta `backend/src/domain/strategies/`
- testes unitarios novos para os contratos centrais extraidos

Se algum item for consolidado em outro formato, isso deve ser registrado aqui.

## 8. Prioridades Tecnicas

## 8.1 Prioridade P0

- `RiskSnapshot`
- regras de health factor
- kill switch
- `PortfolioState`
- `StrategyDecision`
- porta do LLM com fallback

## 8.2 Prioridade P1

- extração inicial de `AccumulatorStrategy`
- extração inicial de `BTCLiteStrategy`
- comparação de cenarios congelados

## 8.3 Prioridade P2

- cobertura de estratégias secundarias
- refinamentos de ergonomia da pasta `domain`

## 9. Checklist Operacional

### 9.1 Estrutura Inicial

- [ ] Criar estrutura inicial de `backend/src/domain/`.
- [ ] Criar modulo `domain/risk`.
- [ ] Criar modulo `domain/portfolio`.
- [ ] Criar modulo `domain/strategies`.
- [ ] Registrar notas de design da extracao.

### 9.2 Extracao de Risco

- [ ] Extrair calculo puro de health factor.
- [ ] Extrair classificacao de health status.
- [ ] Extrair regra de kill switch por drawdown.
- [ ] Extrair validacao de leverage constraints.
- [ ] Extrair reserve policy/gas reserve.

### 9.3 Extracao de Portfolio

- [ ] Extrair consolidacao de tesourarias.
- [ ] Extrair calculo de total equity.
- [ ] Extrair exposicao liquida em BTC.
- [ ] Extrair invariantes de consistencia de carteira.

### 9.4 Extracao de Decisao

- [ ] Criar construcao canonica de `RiskSnapshot`.
- [ ] Criar construcao canonica de `PortfolioState`.
- [ ] Criar montagem de `StrategyDecision` sem side effect.
- [ ] Separar sinal quantitativo de decisao final.
- [ ] Garantir que a decisao final respeita veto de risco.

### 9.5 Porta do LLM

- [ ] Criar porta unica de consulta ao LLM.
- [ ] Reusar contrato `RiskDecisionContext`.
- [ ] Reusar contrato `LLMDecisionResponse`.
- [ ] Unificar validacao estrutural da resposta.
- [ ] Garantir fallback heuristico com a mesma interface.
- [ ] Garantir rastreabilidade de `source=llm` e `source=fallback`.

### 9.6 Estrategias Prioritarias

- [ ] Isolar parte declarativa da `AccumulatorStrategy`.
- [ ] Isolar parte declarativa da `BTCLiteStrategy`.
- [ ] Evitar side effect direto nas regras novas de decisao.
- [ ] Manter paridade comportamental nos cenarios P0.

### 9.7 Testes de Dominio

- [ ] Criar testes unitarios de `RiskSnapshot`.
- [ ] Criar testes unitarios de `PortfolioState`.
- [ ] Criar testes unitarios de `StrategyDecision`.
- [ ] Criar testes unitarios do contrato do LLM.
- [ ] Criar testes de fallback deterministico.

### 9.8 Comparacao com Legado

- [ ] Definir cenarios congelados de comparacao.
- [ ] Comparar decisao nova versus legado em cenarios criticos.
- [ ] Registrar divergencias aceitas e divergencias indesejadas.
- [ ] Produzir relatorio de comparacao da fase.

### 9.9 Fechamento

- [ ] Consolidar aprendizados em artefatos da fase.
- [ ] Confirmar que o dominio central roda sem banco e sem API.
- [ ] Confirmar que o LLM esta atras de porta unica.
- [ ] Declarar o corte minimo que destrava a Fase 3.

## 10. Primeiro Corte Tecnico Recomendado

Sequencia recomendada para iniciar a implementacao real:

1. criar `domain/risk` com:
   - health factor
   - health status
   - kill switch
2. criar `domain/portfolio` com:
   - total equity
   - treasury split
3. criar `domain/strategies/decision.py` com:
   - `StrategyDecision`
   - validacao de `action`
   - validacao de `amount_pct`
4. criar testes unitarios desses tres blocos
5. so depois ligar isso ao legado

## 11. Perguntas que a Fase Precisa Responder

1. Quais regras do legado ja podem virar dominio puro sem depender do engine inteiro?
2. Como materializar `RiskSnapshot` e `PortfolioState` sem puxar acoplamento acidental?
3. Que parte da estrategia e realmente decisao e que parte e mero side effect operacional?
4. O contrato do LLM ficou realmente reutilizavel ou ainda depende do shape atual do legado?
5. Quais divergencias em relacao ao legado sao correcao intencional e quais sao regressao?

## 12. Criterios de Saida

A Fase 2 so fecha quando:

- existir dominio puro executavel para risco, portfolio e decisao central;
- os testes unitarios P0 estiverem implementados;
- o contrato do LLM estiver encapsulado por uma porta unica;
- pelo menos as estrategias prioritarias estiverem parcialmente extraidas de forma testavel;
- houver comparacao documentada com o legado para cenarios-chave.

## 13. Dependencias para a Fase 3

A Fase 3 depende diretamente desta fase para:

- construir casos de uso sobre dominio puro;
- parar de usar `system_runner.py` como orquestrador central;
- tornar a API uma camada fina;
- reduzir drasticamente o risco de regressao funcional.

## 14. Status

Estado atual da fase:

- Status: `planned`
- Dono atual: `Codex + usuário`
- Documento mestre relacionado: [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md)

## 15. Proximo Passo Imediato

Proximo passo recomendado ainda em modo planejamento:

1. criar `phase-2-design-notes.md`;
2. criar `phase-2-comparison.md`;
3. definir o primeiro corte de execucao autorizado;
4. so depois iniciar implementacao no codigo.

## 16. Observacao Operacional

Este documento e um plano de execucao da fase, nao evidencia de que a fase ja foi executada.
