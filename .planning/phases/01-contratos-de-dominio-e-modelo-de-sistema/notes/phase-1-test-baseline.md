# Fase 1: Baseline de Testes

## 1. Objetivo

Definir a malha minima de testes que precisa nascer junto com a extracao do nucleo puro na Fase 2.

## 2. Leitura Executiva

O objetivo nao e reproduzir toda a suite atual imediatamente. O objetivo e garantir que a reescrita mexa primeiro no que realmente protege produto:

- causalidade temporal;
- risco e kill switch;
- saude de carteira;
- contrato da decisao;
- contrato do LLM;
- consistencia entre `BacktestResult` e `SimulationSummary`.

## 3. Camadas de Teste Recomendadas

## 3.1 Unitarios puros de dominio

Escopo:

- sem banco
- sem FastAPI
- sem provider externo

Prioridade:

- `P0`

## 3.2 Integracao de repositories

Escopo:

- persistencia previsivel
- banco dedicado
- sem depender do banco principal

Prioridade:

- `P1`

## 3.3 Integracao de casos de uso

Escopo:

- wiring entre application, repositories fake/real e dominio

Prioridade:

- `P1`

## 3.4 API smoke

Escopo:

- garantir que rotas chamam casos de uso certos
- sem reproduzir toda a logica no teste da rota

Prioridade:

- `P2`

## 4. Testes P0 que a Fase 2 Deve Implementar Primeiro

## 4.1 `MarketCandle`

- valida OHLC basico
- rejeita candle incoerente
- preserva ordenacao temporal

## 4.2 `FeatureVector`

- garante ausencia de target leakage
- garante `as_of_time` coerente com candle base
- garante presenca apenas de features permitidas

## 4.3 `Prediction`

- aceita confianca valida
- rejeita confianca fora de faixa
- mantem rastreabilidade de tempo e modelo

## 4.4 `RiskSnapshot`

- kill switch prevalece sobre abertura de risco
- health factor critico bloqueia alavancagem
- drawdown global e diario produzem estado coerente

## 4.5 `PortfolioState`

- calcula visao consolidada coerente
- nao permite equity inconsistente com blocos principais
- preserva separacao de tesourarias

## 4.6 `StrategyDecision`

- rejeita acao fora do conjunto permitido
- rejeita `amount_pct` invalido
- respeita veto de `RiskSnapshot`

## 4.7 Contrato do LLM

- parse de JSON puro
- parse de JSON em markdown
- parse de JSON em HTML
- fallback para resposta invalida
- fallback para contexto critico de risco
- diferenciacao entre `source=llm` e `source=fallback`

## 4.8 `BacktestResult` e `SimulationSummary`

- compartilham `run_id`
- preservam datas coerentes
- mantem metricas basicas consistentes
- summary oficial contem campos suficientes para dashboard

## 5. Golden Scenarios Recomendados

## 5.1 Cenario A. Defesa total

Contexto:

- health factor critico
- drawdown elevado
- carteira alavancada

Resultado esperado:

- decisao final defensiva
- nenhum risco novo aberto

## 5.2 Cenario B. Alta conviccao com risco seguro

Contexto:

- `ml_confidence` alto
- health factor seguro
- regime favoravel

Resultado esperado:

- acao agressiva permitida pelo contrato
- sizing dentro do limite esperado

## 5.3 Cenario C. Oversold com baixa conviccao

Contexto:

- RSI muito baixo
- confianca moderada/baixa

Resultado esperado:

- preferencia por `SPOT_ONLY` ou postura conservadora

## 5.4 Cenario D. Resposta invalida do LLM

Contexto:

- provider retorna texto invalido ou acao proibida

Resultado esperado:

- fallback deterministico
- auditoria explicita da troca de origem

## 5.5 Cenario E. Query de dashboard

Contexto:

- existe `SimulationSummary` oficial persistido

Resultado esperado:

- dashboard snapshot monta resposta sem disparar simulacao

## 6. Invariantes que Devem Virar Testes Obrigatorios

- zero look-ahead
- `confidence` entre `0.0` e `1.0`
- `amount_pct` entre `0.0` e `1.0`
- health factor bloqueando risco critico
- kill switch com precedencia
- `SimulationSummary` preservando separacao de tesourarias
- provider invalido nunca gerando acao desconhecida

## 7. Gate Minimo para Extracao Segura

Antes de considerar a Fase 2 operacionalmente segura, precisamos ter:

- testes puros para contratos centrais de dominio
- testes puros do contrato do LLM e fallback
- pelo menos um teste de caso de uso `run_backtest` com dependencias controladas
- pelo menos um teste de consulta `build_dashboard_snapshot` garantindo ausencia de side effect

## 8. O Que Nao Repetir da Suite Atual

- fixture que copia dados do banco principal
- teste de API que reimplementa metade da logica interna via patching excessivo
- acoplamento de teste a nome de DataFrame do legado

## 9. Ordem Recomendada de Implementacao

1. contratos de dominio puros
2. contrato do LLM
3. caso de uso `run_backtest`
4. caso de uso `build_dashboard_snapshot`
5. repositories de persistencia
6. API smoke

## 10. Conclusao

Essa baseline nao tenta cobrir tudo. Ela protege o nucleo que torna a reescrita segura.

Se a Fase 2 respeitar esse gate, a extracao do dominio pode avancar com risco bem menor do que o estado atual do repositorio permite.

