# Fase 7A: Baseline de Regressao

## 1. Objetivo

Este documento define a baseline minima de regressao da `Fase 7A`, que a reescrita precisa preservar antes dos smoke tests de interface da `Fase 7B`.

## 2. Leitura Executiva

A reescrita nao precisa provar tudo de uma vez. Ela precisa provar o suficiente para:

- nao quebrar regras centrais de risco;
- nao corromper predicoes e summaries;
- nao transformar a API em casca bonita com comportamento quebrado;
- nao perder o envelope de seguranca do LLM.

## 3. Principios da Baseline

- baseline minima protege fluxo critico, nao cobertura cosmetica;
- cada baseline deve ser pequena, repetivel e deterministica;
- regressao deve ser medida em contratos e comportamento, nao em detalhes acidentais de implementacao;
- smoke nao substitui unitario, e unitario nao substitui integracao.
- smoke de API/BFF/frontend/WebSocket fica explicitamente fora deste artefato e pertence a `Fase 7B`.

## 4. Fluxos Minimos Obrigatorios

## 4.1 Risco e Portfolio

Precisa proteger:

- kill switch tem precedencia;
- health factor critico bloqueia abertura de novo risco;
- drawdown relevante muda permissao de risco;
- reserva de gas nao desaparece da conta;
- sizing respeita limites definidos.

Gates sugeridos:

- cenarios puros de `RiskSnapshot`;
- cenarios puros de `PortfolioState`;
- cenarios de decisao com e sem permissao de risco.

## 4.2 Predicoes

Precisa proteger:

- `confidence` continua no intervalo esperado;
- predicao e metadados permanecem coerentes;
- thresholds e abstencao continuam interpretados corretamente;
- predição nao vira decisao automaticamente.

Gates sugeridos:

- dataset pequeno de predicoes sinteticas;
- asserts sobre shape, confianca e consistencia temporal.

## 4.3 Simulacao / Backtest

Precisa proteger:

- simulacao gera `summary` oficial;
- trade history e positions continuam coerentes;
- query nao executa simulacao implicitamente;
- resultado basico nao depende de cache oculto.

Gates sugeridos:

- cenario de ouro de run pequeno;
- comparacao entre report e summary;
- verificacao de ausencia de side effect em query.

## 4.4 LLM

Precisa proteger:

- resposta invalida cai em fallback;
- acao fora do conjunto permitido e rejeitada;
- restricoes operacionais continuam valendo;
- envelope de seguranca nao se perde.

Gates sugeridos:

- cenarios de parsing valido;
- cenarios de parsing invalido;
- cenarios de fallback;
- cenarios de politica proibitiva.

## 4.5 Control Center e Contratos de Consulta

Precisa proteger:

- snapshots e consultas centrais continuam coerentes;
- query nao passa a disparar processamento pesado;
- contratos de consulta usados por dashboard/control center permanecem consistentes;
- a camada de aplicacao nao perde semantica ao alimentar a interface.

Gates sugeridos:

- asserts sobre `build_dashboard_snapshot`
- asserts sobre `simulation/status`
- asserts sobre `simulation/summary`
- verificacao de contratos de consulta sem depender ainda do BFF ou do frontend

## 5. Baseline Minima por Fase Executavel

## 5.1 Gate para Fase 2

Obrigatorio:

- risco puro
- portfolio puro
- decisao e envelope do LLM

## 5.2 Gate para Fase 3

Obrigatorio:

- commands e queries centrais com DTOs coerentes;
- query nao dispara command;
- baseline de `run_backtest` e `build_dashboard_snapshot`.

## 5.3 Gate para Fase 5

Obrigatorio:

- contratos centrais prontos para receber smoke de API na `Fase 7B`;
- ausencia de side effect em `GET`;
- payloads centrais formalizados;
- streams centrais com estado operacional claro.

## 5.4 Gate para Fase 6

Obrigatorio:

- BFF e frontend terem contratos suficientemente estabilizados para a `Fase 7B`;
- estados `mock`, `degraded` e `disabled` ficarem modelados.

## 5.5 Gate para Fase 8

Obrigatorio:

- simulacao e paper trading distinguiveis;
- baseline de runtime operacional minima;
- eventos e summaries verificaveis.

## 6. Cenarios de Ouro Recomendados

### Cenario A. Mercado em alta controlada

Valida:

- predicao coerente;
- estrategia ofensiva controlada;
- summary consistente.

### Cenario B. Queda brusca com risco elevado

Valida:

- deleverage;
- fallback de decisao;
- bloqueio de novo risco.

### Cenario C. Regime lateral com baixa confianca

Valida:

- abstencao;
- ausencia de overtrading;
- integridade do summary.

### Cenario D. LLM falha

Valida:

- fallback heuristico;
- restricoes e seguranca mantidas.

## 7. O que Fica Fora da Baseline Minima

- benchmark quantitativo profundo de estrategia;
- comparacao de rentabilidade de longo horizonte;
- teste de performance pesada;
- UI pixel perfect;
- smoke de API, BFF, frontend e WebSocket.

Esses temas podem existir depois, mas nao sao gate minimo da migracao arquitetural.

## 8. Status do Entregavel

- status: `draft-initial`
- pronto para servir de gate conceitual da `Fase 7A`
- deve ser refinado junto dos contratos e da futura execucao da suite
