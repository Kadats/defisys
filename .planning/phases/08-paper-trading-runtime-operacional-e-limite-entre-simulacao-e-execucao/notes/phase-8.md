# Fase 8: Paper Trading, Runtime Operacional e Limite entre Simulacao e Execucao

## 1. Proposito

Este documento operacionaliza a Fase 8 definida em [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md).

Objetivo da fase:

- separar definitivamente backtest, sandbox, paper trading e eventual execucao real;
- definir o runtime de paper trading como produto operacional proprio;
- criar modelo claro de eventos, ordens simuladas, fills simulados e snapshots;
- revisar os limites operacionais entre decisao, simulacao e runtime;
- preparar a base para evolucao segura rumo a execucao mais proxima do real.

Ao final desta fase, o sistema deve ter uma fronteira explicita entre laboratorio historico e runtime operacional controlado.

## 2. Resultado Esperado

Ao concluir a Fase 8, devemos ter:

- definicao formal do que e paper trading no produto;
- runtime de paper trading separado do fluxo de backtest;
- modelo de eventos operacionais e auditoria;
- contratos para ordens simuladas, fills simulados e snapshots;
- kill switch, health checks e alertas alinhados ao runtime;
- checklist de readiness para aproximacao futura de execucao real.

## 3. Regras da Fase

- Esta fase esta aberta apenas como planejamento.
- Nenhuma implementacao de codigo desta fase deve comecar sem autorizacao explicita do usuario.
- Backtest nao deve continuar servindo como substituto informal de runtime.
- Paper trading nao deve herdar semantica de sandbox fake.
- Eventos operacionais precisam ser auditaveis.
- Kill switch e politicas de risco continuam tendo precedencia maxima.
- Nenhuma aproximacao de execucao real deve ser assumida sem fronteira arquitetural clara.

## 3.1 Gate de Execucao

Antes de executar a Fase 8 no codigo, precisamos ter:

- Fases 2 a 7 suficientemente estabilizadas nos contratos centrais;
- casos de uso da Fase 3 descritos e prontos para sustentar loop operacional;
- persistencia, gateways e eventos da Fase 4 descritos e prontos para sustentar runtime;
- baseline de testes da Fase 7 definida;
- API e frontend reconciliados o bastante para observar runtime;
- entendimento claro da diferenca entre simulacao, laboratorio e runtime;
- confirmacao explicita do usuario para iniciar execucao.

## 4. Escopo

Incluido nesta fase:

- definicao do runtime de paper trading;
- separacao conceitual e tecnica entre backtest e paper trading;
- definicao de eventos, ordens simuladas e fills simulados;
- definicao de snapshots operacionais do runtime;
- revisao de health checks, kill switch e alertas;
- definicao de readiness para um futuro executor mais isolado.

Fora do escopo desta fase:

- execucao real em corretora ou on-chain;
- rollout produtivo de ordens reais;
- troca imediata de linguagem por performance;
- infraestrutura final de alta concorrencia sem necessidade comprovada;
- tratar sandbox atual como produto final.

## 5. Dependencias de Entrada

Esta fase depende diretamente de:

- [phase-0-flows.md](/home/luckstyle/repo/private/defisys-v1/phase-0-flows.md)
- [phase-0-invariants.md](/home/luckstyle/repo/private/defisys-v1/phase-0-invariants.md)
- [phase-1-domain-contracts.md](/home/luckstyle/repo/private/defisys-v1/phase-1-domain-contracts.md)
- [phase-1-llm-contract.md](/home/luckstyle/repo/private/defisys-v1/phase-1-llm-contract.md)
- [phase-3.md](/home/luckstyle/repo/private/defisys-v1/phase-3.md)
- [phase-4.md](/home/luckstyle/repo/private/defisys-v1/phase-4.md)
- [phase-5.md](/home/luckstyle/repo/private/defisys-v1/phase-5.md)
- [phase-6.md](/home/luckstyle/repo/private/defisys-v1/phase-6.md)
- [phase-7.md](/home/luckstyle/repo/private/defisys-v1/phase-7.md)

## 6. Workstreams

### WS1. Definicao de Paper Trading

Definir:

- o que caracteriza paper trading no produto;
- diferenca entre sandbox, backtest e runtime paper;
- quais entradas sao real-time;
- quais saidas sao eventos operacionais auditaveis.

### WS2. Runtime e Loop Operacional

Planejar:

- loop de ingestao controlada;
- loop de decisao;
- geracao de ordem simulada;
- reconciliacao de fill simulado;
- atualizacao de snapshot do runtime.

### WS3. Modelo de Eventos

Definir eventos para:

- market tick ou snapshot;
- decision generated;
- order proposed;
- order accepted/rejected;
- fill simulated;
- risk intervention;
- runtime snapshot;
- runtime alert.

### WS4. Risco Operacional

Definir:

- comportamento do kill switch em runtime;
- bloqueios de abertura;
- sinais de degradacao;
- health checks de runtime;
- politicas de alertas.

### WS5. Auditoria e Observabilidade

Planejar:

- trilha de eventos do runtime;
- logs operacionais;
- dashboards ou snapshots de acompanhamento;
- evidencia minima para auditoria de decisoes.

### WS6. Fronteira para Futuro Executor

Definir:

- o que ainda pode rodar dentro do backend principal;
- o que, no futuro, justificaria extracao para servico separado;
- quais sinais mostrariam necessidade real de um executor mais isolado;
- quando faria sentido avaliar `Go` como runtime especializado.

## 7. Entregaveis da Fase

Arquivos esperados ao final da Fase 8:

- `phase-8.md`
- `phase-8-paper-trading-model.md`
- `phase-8-runtime-events.md`
- `phase-8-risk-and-alerting.md`
- `phase-8-readiness-checklist.md`

Entregaveis de codigo esperados quando houver execucao:

- runtime de paper trading separado do backtest;
- contratos de eventos e snapshots;
- trilha minima de auditoria;
- controles operacionais de risco e alertas.

## 8. Decisoes Tecnicas Recomendadas

- tratar paper trading como runtime orientado a evento, nao como backtest disfarçado;
- manter backtest como trilha historica separada;
- preservar LLM como parte da decisao, com envelope auditavel;
- registrar eventos e snapshots de forma observavel;
- adiar decisao de servico em outra linguagem ate haver pressao operacional real;
- avaliar extracao de executor isolado so quando concorrencia, resiliencia e operacao continua justificarem isso.

## 9. Checklist Operacional

### 9.1 Modelo de Produto

- [ ] Definir papel oficial de paper trading.
- [ ] Separar paper trading de sandbox.
- [ ] Separar paper trading de backtest.
- [ ] Definir objetivo operacional do runtime.

### 9.2 Runtime

- [ ] Definir loop de ingestao.
- [ ] Definir loop de decisao.
- [ ] Definir ordem simulada.
- [ ] Definir fill simulado.
- [ ] Definir snapshot de runtime.

### 9.3 Eventos

- [ ] Definir taxonomia de eventos do runtime.
- [ ] Definir payload minimo por evento.
- [ ] Definir ordenacao e rastreabilidade.
- [ ] Definir correlacao entre decisao, ordem e fill.

### 9.4 Risco e Alertas

- [ ] Definir kill switch em runtime.
- [ ] Definir health checks operacionais.
- [ ] Definir alertas minimos.
- [ ] Definir bloqueios de risco por estado.

### 9.5 Auditoria

- [ ] Definir trilha minima de auditoria.
- [ ] Definir logs operacionais.
- [ ] Definir snapshots observaveis.
- [ ] Definir evidencias minimas por decisao.

### 9.6 Fronteira de Execucao Futura

- [ ] Definir o que continua no backend principal.
- [ ] Definir o que pode virar servico separado.
- [ ] Definir sinais para considerar executor em outra linguagem.
- [ ] Definir readiness para aproximacao de execucao real.

### 9.7 Fechamento

- [ ] Consolidar aprendizados em artefatos da fase.
- [ ] Confirmar que paper trading nao depende de fluxo confuso de backtest.
- [ ] Confirmar que runtime e auditavel.
- [ ] Declarar o corte minimo que destrava a Fase 9.

## 10. Primeiro Corte Tecnico Recomendado

Sequencia recomendada para a futura execucao:

1. formalizar o modelo de paper trading e sua diferenca para backtest;
2. definir eventos e snapshots do runtime;
3. integrar kill switch, health checks e alertas;
4. montar trilha minima de auditoria;
5. so depois avaliar se o runtime exige extracao para servico mais isolado.

## 11. Perguntas que a Fase Precisa Responder

1. O que exatamente diferencia paper trading de backtest neste produto?
2. Quais eventos minimos tornam o runtime auditavel?
3. Como o kill switch atua em runtime sem ambiguidade?
4. Quando faria sentido extrair um executor mais isolado?
5. Qual o criterio de readiness antes de qualquer passo rumo a execucao real?

## 12. Criterios de Saida

A Fase 8 so fecha quando:

- houver modelo claro de paper trading;
- backtest e runtime estiverem separados conceitualmente e tecnicamente;
- eventos e snapshots do runtime estiverem definidos;
- risco operacional e alertas estiverem planejados;
- existir checklist objetivo de readiness para evolucao futura.

## 13. Dependencias para a Fase 9

A Fase 9 depende diretamente desta fase para:

- decidir o que do legado ainda pode ser aposentado;
- consolidar a arquitetura final em torno de fluxos reais;
- evitar cutover para uma base que ainda mistura laboratorio e runtime;
- fechar a documentacao final de arquitetura e operacao.

## 14. Status

Estado atual da fase:

- Status: `planned`
- Dono atual: `Codex + usuário`
- Documento mestre relacionado: [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md)

## 15. Proximo Passo Imediato

Planejamento da fase consolidado com os seguintes artefatos:

1. `phase-8-paper-trading-model.md`
2. `phase-8-runtime-events.md`
3. `phase-8-risk-and-alerting.md`
4. `phase-8-readiness-checklist.md`

Proximo passo recomendado:

1. abrir o planejamento da Fase 9;
2. so depois iniciar execucao da Fase 8 quando houver autorizacao explicita do usuario.

## 16. Observacao Operacional

Este documento e um plano de execucao da fase, nao evidencia de que a fase ja foi executada.
