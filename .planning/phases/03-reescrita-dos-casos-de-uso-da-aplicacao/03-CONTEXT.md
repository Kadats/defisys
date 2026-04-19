# Fase 3: Reescrita dos Casos de Uso da Aplicacao

## 1. Proposito

Este documento operacionaliza a Fase 3 definida em [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md).

Objetivo da fase:

- parar de usar `api.py` e `system_runner.py` como orquestradores centrais;
- explicitar os casos de uso da aplicacao;
- fazer a camada de aplicacao depender de contratos claros e de interfaces abstratas;
- preparar a futura migracao da API para uma casca fina.

Ao final desta fase, o fluxo principal deve estar representado por casos de uso nomeados, com DTOs internos, independentes de FastAPI.

## 2. Resultado Esperado

Ao concluir a Fase 3, devemos ter:

- pasta `application/commands`;
- pasta `application/queries`;
- DTOs internos para comandos e consultas principais;
- servicos de orquestracao desacoplados da web;
- fluxo principal rodando por casos de uso;
- `api.py` e `system_runner.py` reduzidos a wrappers temporarios ou adaptadores.

## 3. Regras da Fase

- Esta fase esta aberta apenas como planejamento.
- Nenhuma implementacao de codigo desta fase deve comecar sem autorizacao explicita do usuario.
- Nenhum caso de uso pode conhecer FastAPI diretamente.
- Nenhum caso de uso deve conhecer `pandas.read_sql`, rota HTTP ou websocket.
- A camada de aplicacao pode orquestrar, mas nao pode conter regra de negocio central que deveria estar no dominio.
- Query nao dispara command.

## 3.1 Gate de Execucao

Antes de executar a Fase 3 no codigo, precisamos ter:

- Fase 2 executada ao menos para os fluxos centrais;
- contratos de dominio minimamente implementados para risco, portfolio e decisao;
- baseline inicial de testes da Fase 2 ativa;
- confirmacao explicita do usuario para iniciar execucao.

## 4. Escopo

Incluido nesta fase:

- criacao de comandos e consultas da camada `application`;
- definicao dos DTOs internos de entrada e saida;
- separacao do fluxo principal em casos de uso explicitos;
- retirada gradual de orquestracao de `api.py` e `system_runner.py`;
- definicao de services internos onde realmente fizer sentido.

Fora do escopo desta fase:

- reescrita total da API;
- troca total da persistencia;
- migracao completa de todos os endpoints;
- redesign do frontend;
- reescrita completa do `TradingEngine`.

## 5. Dependencias de Entrada

Esta fase depende diretamente de:

- [phase-1-use-cases.md](/home/luckstyle/repo/private/defisys-v1/phase-1-use-cases.md)
- [phase-1-domain-contracts.md](/home/luckstyle/repo/private/defisys-v1/phase-1-domain-contracts.md)
- [phase-2.md](/home/luckstyle/repo/private/defisys-v1/phase-2.md)

## 6. Workstreams

### WS1. Commands

Criar casos de uso de comando para:

- `sync_market_data`
- `prepare_features`
- `train_model`
- `generate_predictions`
- `run_backtest`
- `run_paper_trading` (quando fizer sentido)

### WS2. Queries

Criar casos de uso de consulta para:

- `build_dashboard_snapshot`
- `get_simulation_status`
- `get_trade_history`
- `get_positions`
- `get_treasuries_summary`
- `get_control_center_snapshot`

### WS3. DTOs

Definir:

- inputs de comando;
- outputs de comando;
- inputs de consulta;
- outputs de consulta;
- contratos de erro e warning quando necessario.

### WS4. Adaptadores de Legado

Planejar:

- como `api.py` passa a delegar para os casos de uso;
- como `system_runner.py` deixa de ser centro da orquestracao;
- quais wrappers temporarios ficam durante a transicao.

### WS5. Validacao da Aplicacao

Definir:

- smoke tests da camada de aplicacao;
- pontos de comparacao com o legado;
- como evitar que query continue disparando simulacao pesada.

## 7. Entregaveis da Fase

Arquivos esperados ao final da Fase 3:

- `phase-3.md`
- `phase-3-use-case-map.md`
- `phase-3-dto-map.md`
- `phase-3-transition-plan.md`

Entregaveis de codigo esperados quando houver execucao:

- `backend/src/application/commands/`
- `backend/src/application/queries/`
- `backend/src/application/dto/`
- wrappers temporarios no legado

## 8. Casos de Uso Prioritarios

## 8.1 Commands P0

- `run_backtest`
- `train_model`
- `generate_predictions`

## 8.2 Queries P0

- `build_dashboard_snapshot`
- `get_simulation_status`
- `get_treasuries_summary`

## 8.3 Fluxos P1

- `sync_market_data`
- `prepare_features`
- `get_trade_history`
- `get_positions`

## 9. Checklist Operacional

### 9.1 Mapa de Casos de Uso

- [ ] Mapear commands definitivos.
- [ ] Mapear queries definitivas.
- [ ] Separar fluxos obrigatorios de fluxos secundarios.
- [ ] Confirmar qual e o fluxo principal do produto nesta fase.

### 9.2 DTOs

- [ ] Definir DTOs de comando.
- [ ] Definir DTOs de consulta.
- [ ] Definir outputs estruturados.
- [ ] Definir tratamento de warnings e falhas.

### 9.3 Adaptacao do Legado

- [ ] Mapear `api.py` para commands e queries.
- [ ] Mapear `system_runner.py` para commands e queries.
- [ ] Registrar wrappers temporarios.
- [ ] Registrar comportamento legado que deve morrer nesta fase.

### 9.4 Regras de Arquitetura

- [ ] Confirmar que command nao conhece FastAPI.
- [ ] Confirmar que query nao dispara simulacao.
- [ ] Confirmar que a camada de aplicacao depende apenas de interfaces abstratas.
- [ ] Confirmar que regra de negocio central continua no dominio.

### 9.5 Validacao

- [ ] Definir smoke tests da camada de aplicacao.
- [ ] Definir cenarios de comparacao com o legado.
- [ ] Definir gate minimo para considerar a fase segura.

### 9.6 Fechamento

- [ ] Consolidar aprendizados em artefatos da fase.
- [ ] Declarar o corte minimo que destrava a Fase 4.
- [ ] Confirmar que a API pode virar adaptador fino na fase seguinte.

## 10. Primeiro Corte Tecnico Recomendado

Sequencia recomendada para a futura execucao:

1. criar DTOs de `RunBacktestInput/Output`;
2. criar DTOs de `BuildDashboardSnapshotInput/Output`;
3. criar command `run_backtest`;
4. criar query `build_dashboard_snapshot`;
5. adaptar o legado para delegar a esses dois casos de uso primeiro.

## 11. Perguntas que a Fase Precisa Responder

1. Quais casos de uso precisam existir obrigatoriamente para o fluxo principal rodar?
2. O que ainda deve ficar temporariamente em `system_runner.py`?
3. Como impedir que a camada de aplicacao vire apenas outro monolito?
4. Quais queries oficiais precisam existir antes da reescrita da API?
5. Qual o menor corte de migracao que já reduz acoplamento sem quebrar paridade?

## 12. Criterios de Saida

A Fase 3 so fecha quando:

- os casos de uso principais estiverem definidos e implementados;
- os DTOs internos estiverem claros;
- o fluxo principal nao depender mais de `api.py` e `system_runner.py` como centros da regra;
- endpoints antigos puderem atuar como wrappers simples.

## 13. Dependencias para a Fase 4

A Fase 4 depende diretamente desta fase para:

- conectar repositories e gateways novos aos casos de uso;
- reduzir drasticamente o acoplamento da web com o banco;
- preparar a API para modularizacao real.

## 14. Status

Estado atual da fase:

- Status: `planned`
- Dono atual: `Codex + usuário`
- Documento mestre relacionado: [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md)

## 15. Proximo Passo Imediato

Proximo passo recomendado ainda em modo planejamento:

1. criar `phase-3-use-case-map.md`;
2. criar `phase-3-dto-map.md`;
3. criar `phase-3-transition-plan.md`;
4. so depois abrir execucao quando a Fase 2 estiver realmente implementada.

## 16. Observacao Operacional

Este documento e um plano de execucao da fase, nao evidencia de que a fase ja foi executada.
