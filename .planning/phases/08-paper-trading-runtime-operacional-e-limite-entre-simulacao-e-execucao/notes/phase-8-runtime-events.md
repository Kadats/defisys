# Fase 8: Eventos do Runtime Operacional

## 1. Objetivo

Este documento define a taxonomia de eventos do runtime de paper trading.

## 2. Leitura Executiva

Sem evento estruturado, paper trading vira apenas “simulacao rodando em loop”. O objetivo aqui e tornar o runtime auditavel e observavel.

## 3. Principios dos Eventos

- cada evento precisa ter tipo claro;
- eventos precisam ser ordenaveis no tempo;
- decisao, ordem e fill precisam ser correlacionaveis;
- evento deve carregar contexto suficiente para auditoria;
- evento tecnico e evento de dominio nao devem ser confundidos.

## 4. Envelope Canonico de Evento

Shape conceitual recomendado:

```text
{
  event_id,
  session_id,
  event_type,
  occurred_at,
  correlation_id,
  source,
  payload
}
```

Campos recomendados:

- `event_id`
- `session_id`
- `event_type`
- `occurred_at`
- `correlation_id`
- `source`
- `payload`

## 5. Tipos de Evento Recomendados

## 5.1 Mercado

- `market_snapshot_received`
- `market_data_degraded`

Payload minimo:

- `symbol`
- `timeframe`
- `price`
- `source_status`

## 5.2 Decisao

- `decision_context_built`
- `llm_consulted`
- `llm_fallback_used`
- `strategy_decision_generated`
- `strategy_decision_blocked`

Payload minimo:

- `strategy_name`
- `risk_state`
- `ml_confidence`
- `market_regime`
- `decision_action`
- `decision_source`

## 5.3 Ordem

- `paper_order_proposed`
- `paper_order_rejected`
- `paper_order_accepted`
- `paper_order_canceled`

Payload minimo:

- `order_id`
- `action`
- `quantity`
- `reference_price`
- `reason`

## 5.4 Fill

- `paper_fill_simulated`
- `paper_fill_failed`

Payload minimo:

- `fill_id`
- `order_id`
- `fill_price`
- `fill_quantity`
- `slippage_bps`

## 5.5 Portfolio e Runtime

- `portfolio_snapshot_updated`
- `risk_snapshot_updated`
- `runtime_snapshot_emitted`
- `runtime_state_changed`

Payload minimo:

- `portfolio_equity_usd`
- `cash_usd`
- `health_factor`
- `kill_switch_active`
- `runtime_status`

## 5.6 Alertas

- `runtime_warning_emitted`
- `runtime_alert_emitted`
- `kill_switch_activated`
- `kill_switch_cleared`

Payload minimo:

- `severity`
- `code`
- `message`
- `blocking`

## 6. Correlacao Entre Eventos

Regra recomendada:

- uma cadeia decisao -> ordem -> fill deve compartilhar `correlation_id`;
- eventos tecnicos relacionados ao mesmo ciclo tambem devem poder ser agrupados;
- isso e essencial para auditoria e depuracao.

## 7. Eventos Obrigatorios na Primeira Versao

Conjunto minimo:

- `market_snapshot_received`
- `strategy_decision_generated`
- `llm_fallback_used` quando ocorrer
- `paper_order_proposed`
- `paper_order_rejected` ou `paper_order_accepted`
- `paper_fill_simulated`
- `runtime_snapshot_emitted`
- `kill_switch_activated` quando ocorrer

## 8. O que Nao Deve Virar Evento de Dominio

- log de debug irrelevante;
- stack trace tecnico cru;
- ping/heartbeat interno sem valor auditavel;
- ruído de infraestrutura que nao afeta decisao ou operacao.

Esses itens podem existir em logging tecnico, mas nao como evento canonico do runtime.

## 9. Persistencia e Observabilidade

Direcao recomendada:

- eventos importantes devem ser persistiveis;
- snapshots podem ser persistidos ou derivados, dependendo do custo;
- logs tecnicos complementam, mas nao substituem, o modelo de evento;
- UI e observabilidade devem conseguir consumir pelo menos parte desses eventos.

## 10. Status do Entregavel

- status: `draft-initial`
- pronto para orientar a trilha de eventos do runtime da Fase 8
- deve ser refinado junto da futura execucao da fase
