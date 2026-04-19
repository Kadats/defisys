# Fase 9: Plano de Cutover

## 1. Objetivo

Este documento define como o cutover para a arquitetura nova deve acontecer.

## 2. Leitura Executiva

O cutover nao deve ser um “big bang” cego. A troca precisa acontecer em ondas pequenas, com rollback simples e baseline validada.

## 3. Principios do Cutover

- trocar um ponto de entrada oficial por vez;
- validar baseline entre cada onda;
- remover dependencia do legado apenas quando o substituto estiver estavel;
- manter rollback simples e objetivo;
- registrar cada corte de forma explicita.

## 4. Ondas Recomendadas

## 4.1 Onda 1. Backend Oficial

Objetivo:

- definir o ponto de entrada oficial do backend novo;
- reduzir `backend/src/api.py` a bootstrap ou removê-lo como centro da regra;
- parar de depender de `system_runner.py` como orquestrador central.

Checklist:

- wiring novo validado;
- smoke da API ok;
- compatibilidade critica ainda ativa quando necessario.

Rollback:

- restaurar ponto de entrada anterior;
- reativar aliases temporarios necessarios.

## 4.2 Onda 2. Frontend e BFF Oficiais

Objetivo:

- fazer `frontend/` consumir apenas contratos canonicos;
- simplificar proxies/BFF para seu papel final;
- garantir que a UI nao dependa de mock oculto.

Checklist:

- BFF alinhado;
- UI principal validada;
- estados `mock`, `degraded` e `disabled` visiveis.

Rollback:

- reativar adaptadores de compatibilidade da Fase 5 e 6;
- reverter consumers para aliases temporarios.

## 4.3 Onda 3. Remocao de Compatibilidade

Objetivo:

- retirar aliases de rota;
- retirar adaptadores de payload;
- retirar aliases de WebSocket;
- reduzir o sistema a contratos oficiais.

Checklist:

- ausencia de consumidor ativo do legado;
- baseline verde;
- docs atualizadas.

Rollback:

- reativar alias especifico que falhou;
- nao reabrir compatibilidade em massa sem necessidade.

## 4.4 Onda 4. Limpeza Final

Objetivo:

- remover pontos de entrada obsoletos;
- consolidar scripts, docs e docker;
- fechar o estado final do repo.

Checklist:

- nenhum modulo principal depende do legado;
- docs e comandos oficiais coerentes;
- runbook minimo pronto.

## 5. Gates Entre Ondas

Cada onda so avanca quando:

- baseline da Fase 7 passa;
- smoke de API/BFF/UI relevante passa;
- plano de rollback da onda seguinte esta claro;
- nao ha regressao critica aberta.

## 6. Sinais de que o Cutover Pode Prosseguir

- marcos de paridade atendidos;
- contratos canonicos em uso pelos consumidores principais;
- ausencia de dependencia operacional do legado;
- compatibilidade temporaria restando apenas por itens marginais.

## 7. Sinais de que o Cutover Deve Ser Adiado

- frontend ainda depende de payload legado central;
- runtime ainda mistura backtest e paper trading;
- baseline de regressao instavel;
- rollback pouco claro;
- docs e scripts ainda induzem fluxo antigo como principal.

## 8. Status do Entregavel

- status: `draft-initial`
- pronto para orientar a estrategia de corte da Fase 9
- deve ser refinado antes da execucao real do cutover
