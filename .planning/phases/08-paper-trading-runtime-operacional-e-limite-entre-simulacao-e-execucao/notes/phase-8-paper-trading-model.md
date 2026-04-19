# Fase 8: Modelo de Paper Trading

## 1. Objetivo

Este documento define o modelo conceitual de paper trading do produto.

## 2. Leitura Executiva

Conclusao principal:

- paper trading nao e backtest historico;
- paper trading nao e sandbox fake;
- paper trading e um runtime operacional controlado, sem capital real, que observa mercado, toma decisao, gera ordem simulada, registra fill simulado e produz trilha auditavel.

## 3. Definicao Canonica

Paper trading no DefiSys deve significar:

- ingestao de dados em tempo operacional;
- uso da mesma logica de decisao central;
- aplicacao dos mesmos guardrails de risco;
- sem envio de ordem real;
- com eventos, ordens e fills simulados registrados.

## 4. Diferenca Entre Modos do Produto

## 4.1 Backtest

Natureza:

- historico
- dataset fechado
- replay analitico

Finalidade:

- avaliar estrategia e parametros em janela passada

Saida principal:

- `BacktestResult`
- `SimulationSummary`

## 4.2 Sandbox

Natureza:

- laboratorio
- UX de exploracao
- pode usar dados ou comportamento fake

Finalidade:

- experimentar hipoteses e interfaces

Regra:

- nao pode ser confundido com runtime operacional.

## 4.3 Paper Trading

Natureza:

- runtime controlado
- sem capital real
- com loop continuo ou semi-continuo

Finalidade:

- validar comportamento operacional da estrategia e da pilha sem executar ordens reais

Saida principal:

- eventos
- ordens simuladas
- fills simulados
- snapshots de runtime

## 4.4 Execucao Real Futura

Natureza:

- operacional
- sensivel
- com capital real e barreiras adicionais

Regra:

- fica fora do escopo atual.

## 5. Entradas do Runtime de Paper Trading

Entradas minimas recomendadas:

- market snapshots ou ticks controlados;
- estado de portfolio paper;
- risk snapshot;
- predicao mais recente;
- contexto do LLM;
- estado do runtime.

Entradas auxiliares:

- health checks;
- configuracao de ambiente;
- flags de kill switch;
- alertas.

## 6. Saidas do Runtime de Paper Trading

Saidas minimas recomendadas:

- `strategy_decision`
- `paper_order`
- `paper_fill`
- `portfolio_snapshot`
- `risk_snapshot`
- `runtime_snapshot`
- `runtime_event`

## 7. Entidades e Contratos Recomendados

## 7.1 `PaperTradingSession`

Campos conceituais:

- `session_id`
- `environment`
- `strategy_name`
- `started_at`
- `ended_at`
- `status`

## 7.2 `PaperOrder`

Campos conceituais:

- `order_id`
- `session_id`
- `created_at`
- `action`
- `symbol`
- `quantity`
- `reference_price`
- `reason`
- `decision_ref`
- `status`

Status sugeridos:

- `proposed`
- `accepted`
- `rejected`
- `filled`
- `canceled`

## 7.3 `PaperFill`

Campos conceituais:

- `fill_id`
- `order_id`
- `filled_at`
- `fill_price`
- `fill_quantity`
- `slippage_bps`
- `fill_source`

## 7.4 `RuntimeSnapshot`

Campos conceituais:

- `session_id`
- `timestamp`
- `portfolio_equity_usd`
- `cash_usd`
- `net_btc_exposure`
- `risk_state`
- `runtime_health`
- `open_orders_count`
- `open_positions_count`

## 8. Loop Operacional Recomendado

Sequencia conceitual:

1. receber market snapshot;
2. atualizar contexto e portfolio paper;
3. calcular risk snapshot;
4. gerar decision context;
5. consultar LLM quando aplicavel;
6. validar decisao sob guardrails;
7. propor ordem simulada;
8. simular fill conforme politica definida;
9. atualizar portfolio e snapshot;
10. emitir eventos e auditoria.

## 9. Politica de Simulacao de Ordem e Fill

Direcao recomendada:

- fill simulado nao deve ser trivialmente igual ao preco de referencia sem explicacao;
- politica de fill deve ser simples, auditavel e deterministica na primeira versao;
- qualquer slippage ou delay simulado precisa ser controlado por regra clara.

Primeira versao recomendada:

- `fill_source = paper_engine`
- referencia por ultimo preco conhecido ou snapshot de mercado;
- slippage model simplificado e documentado.

## 10. Regras de Risco no Runtime

- kill switch bloqueia novas ordens;
- health factor critico bloqueia aumento de risco;
- drawdown pode forcar modo defensivo;
- degradacao de dados pode impedir decisao ofensiva;
- fallback do LLM continua obrigatorio quando a IA falhar.

## 11. O que o Paper Trading Precisa Provar

- que a decisao do sistema e operacionalmente observavel;
- que a pilha aguenta loop de decisao sem capital real;
- que a telemetria e suficiente para diagnostico;
- que os guardrails continuam acima da estrategia;
- que laboratorio e runtime nao estao mais misturados.

## 12. Status do Entregavel

- status: `draft-initial`
- pronto para orientar o desenho do runtime de paper trading na Fase 8
- deve ser refinado quando a fase entrar em execucao
