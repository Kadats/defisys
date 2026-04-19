# Fase 5: Reescrita da API e dos WebSockets

## 1. Proposito

Este documento operacionaliza a Fase 5 definida em [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md).

Objetivo da fase:

- transformar a API em uma casca fina;
- quebrar o monolito de `backend/src/api.py` em modulos coerentes;
- fazer cada rota depender de um caso de uso explicito;
- padronizar contratos HTTP e politica de compatibilidade;
- tornar o estado dos WebSockets explicito: real, mock ou desativado.

Ao final desta fase, a camada web deve parar de concentrar regra de negocio, acesso direto ao banco, fallback ad hoc e comportamento operacional pesado.

## 2. Resultado Esperado

Ao concluir a Fase 5, devemos ter:

- rotas organizadas por dominio funcional;
- schemas HTTP estaveis e versionados;
- camada de dependencies/injecao para conectar casos de uso e adaptadores;
- startup hooks revisados e sem efeitos colaterais indevidos;
- politica formal de compatibilidade para endpoints legados;
- WebSockets com contrato, status operacional e responsabilidade definidos.

## 3. Regras da Fase

- Esta fase esta aberta apenas como planejamento.
- Nenhuma implementacao de codigo desta fase deve comecar sem autorizacao explicita do usuario.
- Nenhuma rota deve conter regra de negocio central.
- Nenhuma rota deve acessar banco diretamente.
- Nenhum WebSocket principal deve esconder comportamento mockado sem identificacao explicita.
- Query HTTP nao deve disparar processamento pesado ou simulacao.
- Compatibilidade com consumidores atuais deve ser planejada antes de remover endpoints antigos.

## 3.1 Gate de Execucao

Antes de executar a Fase 5 no codigo, precisamos ter:

- Fase 3 executada ao menos para os casos de uso centrais;
- Fase 4 executada ao menos para repositories e gateways criticos;
- mapa oficial da superficie publica atual consolidado;
- estrategia de compatibilidade de payloads aprovada;
- confirmacao explicita do usuario para iniciar execucao.

## 4. Escopo

Incluido nesta fase:

- modularizacao da API por dominio funcional;
- definicao dos schemas de request/response;
- criacao da camada de dependencies da interface web;
- revisao dos startup hooks;
- definicao da politica dos WebSockets;
- plano de convivencia entre endpoints legados e novos;
- limpeza de comportamento de consulta que hoje dispara execucao.

Fora do escopo desta fase:

- reescrita do dominio;
- reescrita dos casos de uso;
- reescrita completa da persistencia;
- reconciliacao total do frontend;
- corte definitivo de todos os endpoints legados no primeiro passo.

## 5. Dependencias de Entrada

Esta fase depende diretamente de:

- [phase-0-endpoints.md](/home/luckstyle/repo/private/defisys-v1/phase-0-endpoints.md)
- [phase-0-flows.md](/home/luckstyle/repo/private/defisys-v1/phase-0-flows.md)
- [phase-0-risks.md](/home/luckstyle/repo/private/defisys-v1/phase-0-risks.md)
- [phase-1-use-cases.md](/home/luckstyle/repo/private/defisys-v1/phase-1-use-cases.md)
- [phase-1-domain-contracts.md](/home/luckstyle/repo/private/defisys-v1/phase-1-domain-contracts.md)
- [phase-3.md](/home/luckstyle/repo/private/defisys-v1/phase-3.md)
- [phase-4.md](/home/luckstyle/repo/private/defisys-v1/phase-4.md)

## 6. Workstreams

### WS1. Modularizacao de Rotas

Definir a estrutura alvo de rotas para:

- `system`
- `market`
- `model`
- `simulation`
- `control_center`
- `paper_trading`

Registrar tambem:

- o que continua em `api.py` apenas como bootstrap;
- o que vira router dedicado;
- o que deve morrer por ser legado improprio.

### WS2. Schemas HTTP

Definir:

- contratos de request;
- contratos de response;
- codigos de erro padrao;
- envelopes de warning quando necessario;
- estrategia de versionamento de payload.

### WS3. Dependencies e Injeção

Definir:

- como a web resolve commands e queries;
- como repositories e gateways entram na interface;
- como evitar acoplamento circular;
- como lidar com wrappers temporarios do legado.

### WS4. WebSockets

Definir para cada stream:

- finalidade;
- origem dos dados;
- frequencia;
- contrato de payload;
- status operacional:
  - real
  - mock
  - disabled

Cobrir explicitamente:

- logs
- pulse
- ticker

### WS5. Startup e Lifecycle

Definir:

- o que pode rodar no startup;
- o que so pode rodar sob comando explicito;
- como sinalizar readiness e health;
- como isolar jobs pesados do bootstrap da API.

### WS6. Compatibilidade e Migracao

Planejar:

- quais endpoints antigos continuam temporariamente;
- quais payloads precisam de adaptador;
- quais aliases vao existir durante a transicao;
- qual o criterio para desativar legado com seguranca.

## 7. Entregaveis da Fase

Arquivos esperados ao final da Fase 5:

- `phase-5.md`
- `phase-5-route-map.md`
- `phase-5-schema-plan.md`
- `phase-5-websocket-plan.md`
- `phase-5-compatibility-plan.md`

Entregaveis de codigo esperados quando houver execucao:

- `backend/src/interfaces/api/routes/`
- `backend/src/interfaces/api/schemas/`
- `backend/src/interfaces/api/dependencies/`
- `backend/src/interfaces/websocket/`
- `backend/src/interfaces/api/app.py` ou equivalente

## 8. Decisoes Tecnicas Recomendadas

- usar `APIRouter` por dominio funcional;
- manter `api.py` apenas como ponto de composicao temporario ou bootstrap;
- introduzir schemas explicitos em vez de dicionarios livres montados na rota;
- tratar WebSocket como interface formal, nao como utilitario acoplado ao monolito;
- manter compatibilidade por tempo limitado e com data de remocao definida;
- explicitar em contrato quando um stream e mockado, nunca esconder isso sob nome de dado real.

## 9. Checklist Operacional

### 9.1 Mapa de Rotas

- [ ] Definir modulos de rota por dominio.
- [ ] Mapear endpoints atuais para routers alvo.
- [ ] Marcar endpoints legados que ficam temporariamente.
- [ ] Marcar endpoints que devem morrer.

### 9.2 Schemas

- [ ] Definir request/response para rotas de system.
- [ ] Definir request/response para rotas de market.
- [ ] Definir request/response para rotas de model.
- [ ] Definir request/response para rotas de simulation.
- [ ] Definir request/response para rotas de control center.
- [ ] Definir codigos de erro e warnings padrao.

### 9.3 Dependencies

- [ ] Definir camada de dependencies da API.
- [ ] Definir como rotas resolvem commands e queries.
- [ ] Definir adaptadores temporarios do legado.
- [ ] Confirmar que a web nao conhece banco diretamente.

### 9.4 WebSockets

- [ ] Definir contrato do stream de logs.
- [ ] Definir contrato do stream de pulse.
- [ ] Definir contrato do stream de ticker.
- [ ] Classificar cada stream como real, mock ou disabled.
- [ ] Definir estrategia de migracao para stream mockado.

### 9.5 Startup e Lifecycle

- [ ] Mapear hooks atuais de startup.
- [ ] Definir o que sai do bootstrap.
- [ ] Definir readiness e health claros.
- [ ] Definir comportamento seguro de inicializacao.

### 9.6 Compatibilidade

- [ ] Mapear payloads que o frontend atual consome.
- [ ] Definir estrategia de alias e deprecacao.
- [ ] Definir janela de convivencia entre antigo e novo.
- [ ] Definir criterio objetivo para remocao do legado.

### 9.7 Fechamento

- [ ] Consolidar aprendizados em artefatos da fase.
- [ ] Confirmar que uma rota corresponde a um caso de uso.
- [ ] Confirmar que query nao dispara execucao pesada.
- [ ] Declarar o corte minimo que destrava a Fase 6.

## 10. Primeiro Corte Tecnico Recomendado

Sequencia recomendada para a futura execucao:

1. modularizar `system` e `simulation`, porque concentram risco e acoplamento mais alto;
2. criar schemas explicitos para health, indicators, logs e simulation status;
3. mover `pulse` e `logs` para uma camada de websocket mais clara;
4. marcar `ticker` oficialmente como `mock` ou substitui-lo por fonte real;
5. so depois migrar os endpoints restantes e reduzir `api.py` ao bootstrap.

## 11. Perguntas que a Fase Precisa Responder

1. Qual a menor divisao de routers que reduz acoplamento sem fragmentar demais a API?
2. Quais payloads do frontend atual estao mais frageis e exigem compatibilidade temporaria?
3. Como impedir definitivamente que query HTTP volte a disparar simulacao ou treino?
4. O que deve acontecer com o ticker mockado antes da reconciliacao do frontend?
5. Qual o corte minimo da nova API que ja permite iniciar a Fase 6 com risco controlado?

## 12. Criterios de Saida

A Fase 5 so fecha quando:

- `api.py` deixar de ser o centro do comportamento web;
- rotas principais dependerem de casos de uso explicitos;
- os payloads centrais estiverem formalizados em schemas;
- os WebSockets principais tiverem status operacional claro;
- os endpoints legados puderem ser tratados como compatibilidade temporaria, nao como centro do sistema.

## 13. Dependencias para a Fase 6

A Fase 6 depende diretamente desta fase para:

- alinhar frontend e backend sobre contratos estaveis;
- remover fallbacks improvisados do BFF;
- deixar claro o que e dado real, derivado ou placeholder;
- reduzir acoplamento entre UI e legado da API.

## 14. Status

Estado atual da fase:

- Status: `planned`
- Dono atual: `Codex + usuário`
- Documento mestre relacionado: [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md)

## 15. Proximo Passo Imediato

Proximo passo recomendado ainda em modo planejamento:

1. criar `phase-5-route-map.md`;
2. criar `phase-5-schema-plan.md`;
3. criar `phase-5-websocket-plan.md`;
4. criar `phase-5-compatibility-plan.md`;
5. so depois abrir execucao quando as Fases 3 e 4 estiverem realmente implementadas.

## 16. Observacao Operacional

Este documento e um plano de execucao da fase, nao evidencia de que a fase ja foi executada.
