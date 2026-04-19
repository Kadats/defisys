# Roadmap: DefiSys v1 Reescrita Parcial

## Overview
Roadmap de migracao gradual para arquitetura com fronteiras claras, preservando regras de negocio e paridade funcional ao longo das fases 0-9.

## Milestones
- 🚧 **v1.0 Reescrita Parcial Guiada** - Phases 0-9 (in progress)

## Phases
- [x] **Phase 0: Congelamento, Baseline e Inventario** - Consolidar baseline tecnico e inventario. (completed 2026-04-19)
- [x] **Phase 1: Contratos de Dominio e Modelo de Sistema** - Definir contratos e linguagem comum. (completed 2026-04-19)
- [x] **Phase 2: Extracao do Nucleo Puro de Risco, Portfolio e Estrategia** - Isolar o dominio puro. (completed 2026-04-19)
- [x] **Phase 3: Reescrita dos Casos de Uso da Aplicacao** - Reestruturar orquestracao de aplicacao. (completed 2026-04-19)
- [x] **Phase 4: Nova Camada de Persistencia e Integracao Externa** - Encapsular infraestrutura. (completed 2026-04-19)
- [x] **Phase 5: Reescrita da API e dos WebSockets** - Migrar interfaces externas do backend. (completed 2026-04-19)
- [x] **Phase 6: Reconciliacao do Frontend e do BFF** - Alinhar frontend ao contrato canonico. (completed 2026-04-19)
- [x] **Phase 7: Reforma da Estrategia de Testes** - Fortalecer qualidade e regressao. (completed 2026-04-19)
- [x] **Phase 8: Paper Trading, Runtime Operacional e Limite entre Simulacao e Execucao** - Validar runtime operacional. (completed 2026-04-19)
- [x] **Phase 9: Cutover, Limpeza e Aposentadoria do Legado** - Completar corte e limpeza final. (completed 2026-04-19)

## Phase Details

### Phase 0: Congelamento, Baseline e Inventario
**Goal**: Registrar baseline tecnico, inventario funcional e riscos da migracao.
**Depends on**: Nothing (first phase)
**Requirements**: [REQ-00]
**Success Criteria** (what must be TRUE):
  1. Inventario de endpoints, dados, fluxos e testes consolidado.
  2. Baseline minima de regressao definida.
**Plans**: 1 plan

Plans:
- [x] 00-01: Consolidar baseline e mapas da Fase 0

### Phase 1: Contratos de Dominio e Modelo de Sistema
**Goal**: Definir contratos de dominio, glossario e modelo de sistema.
**Depends on**: Phase 0
**Requirements**: [REQ-01]
**Success Criteria** (what must be TRUE):
  1. Contratos de dominio documentados e utilizaveis.
  2. Modelo de sistema e casos de uso consolidados.
**Plans**: 1 plan

Plans:
- [x] 01-01: Consolidar contratos e modelo da Fase 1

### Phase 2: Extracao do Nucleo Puro de Risco, Portfolio e Estrategia
**Goal**: Extrair dominio puro e reduzir acoplamentos diretos.
**Depends on**: Phase 1
**Requirements**: [REQ-02]
**Success Criteria** (what must be TRUE):
  1. Componentes de dominio puros definidos e testaveis.
  2. Fronteiras de dependencias explicitadas.
**Plans**: 1 plan

Plans:
- [x] 02-01: Planejamento de extracao do nucleo puro

### Phase 3: Reescrita dos Casos de Uso da Aplicacao
**Goal**: Reestruturar casos de uso da aplicacao com contratos claros.
**Depends on**: Phase 2
**Requirements**: [REQ-03]
**Success Criteria** (what must be TRUE):
  1. Casos de uso principais definidos por contratos.
  2. Orquestracao desacoplada de infraestrutura concreta.
**Plans**: 1 plan

Plans:
- [x] 03-01: Planejamento dos casos de uso da aplicacao

### Phase 4: Nova Camada de Persistencia e Integracao Externa
**Goal**: Encapsular persistencia e gateways de integracao externa.
**Depends on**: Phase 3
**Requirements**: [REQ-04]
**Success Criteria** (what must be TRUE):
  1. Camada de persistencia planejada por repositorios/adaptadores.
  2. Integracoes externas com fronteiras definidas.
**Plans**: 1 plan

Plans:
- [x] 04-01: Planejamento da camada de persistencia e integracao

### Phase 5: Reescrita da API e dos WebSockets
**Goal**: Reestruturar API e canais realtime para contratos estaveis.
**Depends on**: Phase 4
**Requirements**: [REQ-05]
**Success Criteria** (what must be TRUE):
  1. Plano de rotas e compatibilidade definido.
  2. Plano de websocket alinhado a contratos.
**Plans**: 1 plan

Plans:
- [x] 05-01: Planejamento de API e WebSockets

### Phase 6: Reconciliacao do Frontend e do BFF
**Goal**: Alinhar frontend/BFF aos contratos da nova arquitetura.
**Depends on**: Phase 5
**Requirements**: [REQ-06]
**Success Criteria** (what must be TRUE):
  1. Mapa de compatibilidade frontend/BFF estabelecido.
  2. Politicas de estado e rotas consolidadas.
**Plans**: 1 plan

Plans:
- [x] 06-01: Planejamento de reconciliacao frontend e BFF

### Phase 7: Reforma da Estrategia de Testes
**Goal**: Definir baseline robusta de testes para migracao segura.
**Depends on**: Phase 6
**Requirements**: [REQ-07]
**Success Criteria** (what must be TRUE):
  1. Taxonomia de testes e baseline de regressao consolidadas.
  2. Plano de smoke/fixtures aprovado.
**Plans**: 1 plan

Plans:
- [x] 07-01: Planejamento da estrategia de testes

### Phase 8: Paper Trading, Runtime Operacional e Limite entre Simulacao e Execucao
**Goal**: Definir readiness operacional para paper trading e runtime.
**Depends on**: Phase 7
**Requirements**: [REQ-08]
**Success Criteria** (what must be TRUE):
  1. Checklist de readiness e modelo operacional definidos.
  2. Risco, alertas e eventos de runtime mapeados.
**Plans**: 1 plan

Plans:
- [x] 08-01: Planejamento de paper trading e runtime operacional

### Phase 9: Cutover, Limpeza e Aposentadoria do Legado
**Goal**: Planejar e executar o cutover final com rollback seguro.
**Depends on**: Phase 8
**Requirements**: [REQ-09]
**Success Criteria** (what must be TRUE):
  1. Plano de cutover e aposentadoria do legado definido.
  2. Alinhamento final de docs e operacao planejado.
**Plans**: 1 plan

Plans:
- [x] 09-01: Planejamento de cutover final e limpeza

## Progress
| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Congelamento, Baseline e Inventario | 1/1 | Complete    | 2026-04-19 |
| 1. Contratos de Dominio e Modelo de Sistema | 1/1 | Complete    | 2026-04-19 |
| 2. Extracao do Nucleo Puro de Risco, Portfolio e Estrategia | 1/1 | Complete    | 2026-04-19 |
| 3. Reescrita dos Casos de Uso da Aplicacao | 1/1 | Complete    | 2026-04-19 |
| 4. Nova Camada de Persistencia e Integracao Externa | 1/1 | Complete    | 2026-04-19 |
| 5. Reescrita da API e dos WebSockets | 1/1 | Complete    | 2026-04-19 |
| 6. Reconciliacao do Frontend e do BFF | 1/1 | Complete    | 2026-04-19 |
| 7. Reforma da Estrategia de Testes | 1/1 | Complete    | 2026-04-19 |
| 8. Paper Trading, Runtime Operacional e Limite entre Simulacao e Execucao | 1/1 | Complete    | 2026-04-19 |
| 9. Cutover, Limpeza e Aposentadoria do Legado | 1/1 | Complete    | 2026-04-19 |
