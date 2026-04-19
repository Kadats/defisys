# Fase 8: Risco Operacional e Alertas

## 1. Objetivo

Este documento define a politica de risco operacional e alertas do runtime de paper trading.

## 2. Leitura Executiva

No runtime, risco nao e apenas calculo financeiro. Ele passa a incluir:

- saude do portfolio paper;
- saude do pipeline de dados;
- saude do loop operacional;
- degradacao do LLM;
- ativacao de kill switch e bloqueios de ordem.

## 3. Principios

- kill switch continua tendo precedencia maxima;
- runtime degradado nao pode fingir normalidade;
- alertas precisam ser acionaveis;
- risco de dados e risco de carteira devem aparecer separadamente;
- paper trading precisa falhar de forma segura.

## 4. Camadas de Risco no Runtime

## 4.1 Risco de Carteira

Inclui:

- health factor;
- drawdown global;
- drawdown diario;
- exposicao liquida;
- reserva de gas;
- alavancagem simulada.

## 4.2 Risco de Dados

Inclui:

- feed atrasado;
- feed degradado;
- ausencia de predicao valida;
- ausencia de snapshot confiavel;
- mismatch entre fontes.

## 4.3 Risco de Decisao

Inclui:

- LLM indisponivel;
- resposta invalida;
- fallback excessivo;
- conflito entre decisao e guardrail.

## 4.4 Risco Operacional

Inclui:

- loop travado;
- backlog de eventos;
- snapshot desatualizado;
- falha de persistencia;
- perda de observabilidade.

## 5. Estados Operacionais Recomendados

Estados conceituais do runtime:

- `healthy`
- `degraded`
- `restricted`
- `halted`

Semantica:

- `healthy`
  - runtime apto a gerar novas ordens simuladas
- `degraded`
  - runtime funcionando, mas com limitacoes ou fallback
- `restricted`
  - runtime operando com forte reducao de permissao de risco
- `halted`
  - runtime parado para novas ordens

## 6. Kill Switch no Runtime

Regras recomendadas:

- kill switch bloqueia novas ordens imediatamente;
- kill switch gera evento e alerta obrigatorios;
- kill switch nao apaga evidencias do contexto que o disparou;
- retomada apos kill switch precisa de criterio explicito, nao retorno silencioso.

Gatilhos possiveis:

- drawdown acima do limite;
- health factor critico;
- integridade de dados comprometida;
- falha sistemica de runtime;
- comando operacional manual.

## 7. Politica de Alertas

## 7.1 Severidades

- `info`
- `warning`
- `critical`

## 7.2 Alertas Minimos

Alertas obrigatorios:

- feed degradado;
- predicao ausente;
- fallback do LLM recorrente;
- kill switch ativado;
- health factor critico;
- falha de persistencia de evento;
- runtime sem snapshot atualizado.

## 7.3 Campos Minimos do Alerta

- `alert_id`
- `severity`
- `code`
- `message`
- `occurred_at`
- `session_id`
- `blocking`

## 8. Bloqueios de Ordem Recomendados

Uma ordem simulada deve ser bloqueada quando:

- kill switch estiver ativo;
- `can_open_new_risk = false`;
- feed essencial estiver ausente ou degradado acima do permitido;
- contexto de decisao estiver incompleto;
- estado do runtime estiver `halted`;
- politica operacional do ambiente exigir abstencao.

## 9. Comportamento do LLM em Runtime

Regras:

- resposta invalida nao bloqueia o runtime por si so, mas aciona fallback;
- fallback excessivo pode gerar alerta de degradacao;
- LLM nunca sobrepoe kill switch;
- source da decisao precisa permanecer auditavel.

## 10. Observabilidade Minima

O runtime precisa conseguir expor pelo menos:

- estado atual do runtime;
- ultimo snapshot emitido;
- alertas ativos;
- ultimo evento critico;
- quantidade de fallback do LLM em janela recente;
- bloqueios recentes de ordem.

## 11. Status do Entregavel

- status: `draft-initial`
- pronto para orientar risco e alertas do runtime da Fase 8
- deve ser refinado com a definicao final do loop operacional
