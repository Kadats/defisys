# Fase 9: Cutover, Limpeza e Aposentadoria do Legado

## 1. Proposito

Este documento operacionaliza a Fase 9 definida em [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md).

Objetivo da fase:

- trocar os pontos de entrada principais para a nova arquitetura;
- remover adaptadores temporarios e compatibilidades ja vencidas;
- aposentar o que ficou obsoleto no backend, frontend e documentacao;
- alinhar scripts, ambiente, docker e fluxo de desenvolvimento;
- registrar a decisao final de arquitetura pos-migracao.

Ao final desta fase, o sistema principal deve operar pela arquitetura nova, sem depender do “centro nervoso” monolitico antigo.

## 2. Resultado Esperado

Ao concluir a Fase 9, devemos ter:

- backend principal servindo pela nova pilha;
- pontos de entrada legados removidos ou desativados;
- compatibilidades temporarias tratadas e reduzidas;
- README, docs e comandos alinhados com a realidade do repo;
- docker, scripts e ambiente refletindo a arquitetura final;
- plano de manutencao pos-migracao documentado.

## 3. Regras da Fase

- Esta fase esta aberta apenas como planejamento.
- Nenhuma implementacao de codigo desta fase deve comecar sem autorizacao explicita do usuario.
- Cutover so pode acontecer com rollback pensado.
- Compatibilidade temporaria nao pode ser removida sem criterio objetivo.
- Documentacao nao pode ficar para depois do corte.
- Nada deve ser apagado sem saber qual substituto assumiu a funcao.
- O objetivo e remover dependencia do legado, nao apenas mover arquivos de lugar.

## 3.1 Gate de Execucao

Antes de executar a Fase 9 no codigo, precisamos ter:

- Fases 2 a 8 executadas o suficiente para sustentar a arquitetura nova;
- marcos de paridade atendidos para dominio, API e operacao;
- baseline de testes da Fase 7 validando os fluxos centrais;
- estrategia de compatibilidade e remocao do legado aprovada;
- confirmacao explicita do usuario para iniciar execucao.

## 4. Escopo

Incluido nesta fase:

- cutover dos pontos de entrada principais;
- remocao de wrappers e aliases temporarios;
- limpeza de arquivos, caminhos e modulos obsoletos;
- alinhamento de docker, scripts e comandos;
- atualizacao de docs centrais;
- registro da arquitetura final e plano de manutencao.

Fora do escopo desta fase:

- novas features de produto;
- redesign completo de UX;
- troca adicional de stack sem necessidade;
- prolongar compatibilidade por conveniencia indefinidamente;
- inventar nova arquitetura durante o cutover.

## 5. Dependencias de Entrada

Esta fase depende diretamente de:

- [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md)
- [phase-5-compatibility-plan.md](/home/luckstyle/repo/private/defisys-v1/phase-5-compatibility-plan.md)
- [phase-6-compatibility-matrix.md](/home/luckstyle/repo/private/defisys-v1/phase-6-compatibility-matrix.md)
- [phase-7-regression-baseline.md](/home/luckstyle/repo/private/defisys-v1/phase-7-regression-baseline.md)
- [phase-8-readiness-checklist.md](/home/luckstyle/repo/private/defisys-v1/phase-8-readiness-checklist.md)

## 6. Workstreams

### WS1. Cutover de Backend

Planejar:

- qual app, router e wiring passam a ser oficiais;
- como `api.py` legado deixa de ser centro;
- quais pontos de entrada antigos precisam ser desligados;
- como manter rollback controlado.

### WS2. Cutover de Frontend e BFF

Planejar:

- quando o frontend passa a depender apenas dos contratos canonicos;
- quando os proxies/BFF legados podem ser simplificados ou removidos;
- quais aliases ainda permanecem por ultima janela de transicao;
- como confirmar que a UI nao depende mais de mock oculto.

### WS3. Remocao de Compatibilidade Temporaria

Planejar:

- quais aliases de rota saem;
- quais adaptadores de payload saem;
- quais aliases de WebSocket saem;
- quais criterios de remocao devem ser checados antes de apagar cada item.

### WS4. Limpeza de Repo e Estrutura

Planejar:

- limpeza de arquivos monoliticos aposentados;
- limpeza de restos de stack anterior;
- limpeza de scripts e docs obsoletos;
- consolidacao de caminhos oficiais do repo.

### WS5. Ambiente, Docker e Scripts

Planejar:

- atualizacao de `docker-compose.yml`;
- atualizacao de Dockerfiles relevantes;
- revisao de `Makefile` e scripts utilitarios;
- definicao do fluxo oficial de desenvolvimento e operacao local.

### WS6. Documentacao Final

Planejar:

- README principal;
- docs tecnicos centrais;
- narrativa da arquitetura final;
- runbook minimo de manutencao pos-migracao.

### WS7. Plano Pos-Migracao

Definir:

- o que fica monitorado apos o cutover;
- quais debts residuais permanecem;
- quais indicadores mostram se a migracao foi bem sucedida;
- como o time deve evoluir o sistema sem reviver o monolito.

## 7. Entregaveis da Fase

Arquivos esperados ao final da Fase 9:

- `phase-9.md`
- `phase-9-cutover-plan.md`
- `phase-9-legacy-retirement.md`
- `phase-9-docs-and-ops-alignment.md`
- `phase-9-post-migration.md`

Entregaveis de codigo esperados quando houver execucao:

- pontos de entrada novos como oficiais;
- legado desativado ou removido;
- scripts e docker alinhados;
- docs finais coerentes com a arquitetura real.

## 8. Decisoes Tecnicas Recomendadas

- remover compatibilidade em ondas controladas, nao tudo de uma vez;
- manter rollback simples durante o cutover;
- registrar explicitamente o que foi aposentado e por que;
- alinhar documentacao no mesmo movimento do corte;
- tratar o repositorio final como produto mantido, nao como experimento congelado;
- nao deixar aliases, wrappers e mocks residuais por comodidade.

## 9. Checklist Operacional

### 9.1 Backend

- [ ] Definir ponto de entrada oficial do backend.
- [ ] Definir desligamento dos pontos de entrada legados.
- [ ] Definir estrategia de rollback do cutover.
- [ ] Confirmar que o backend principal nao depende do monolito antigo.

### 9.2 Frontend e BFF

- [ ] Definir ponto de entrada oficial do frontend.
- [ ] Confirmar que a UI usa contratos canonicos.
- [ ] Definir remocao de proxies e aliases residuais.
- [ ] Confirmar que nao ha mock oculto em modulos principais.

### 9.3 Compatibilidade

- [ ] Listar compatibilidades que ainda existem.
- [ ] Definir criterio objetivo de remocao por item.
- [ ] Definir ordem de remocao.
- [ ] Definir janelas finais de transicao.

### 9.4 Limpeza de Repo

- [ ] Identificar arquivos e modulos aposentaveis.
- [ ] Identificar restos de stack anterior.
- [ ] Identificar scripts obsoletos.
- [ ] Identificar docs divergentes ou obsoletas.

### 9.5 Ambiente e Operacao

- [ ] Alinhar docker e compose.
- [ ] Alinhar Makefile e comandos oficiais.
- [ ] Alinhar variaveis de ambiente e exemplos.
- [ ] Definir runbook local minimo.

### 9.6 Documentacao

- [ ] Atualizar README principal.
- [ ] Atualizar docs de arquitetura.
- [ ] Registrar decisao final de arquitetura.
- [ ] Registrar manutencao pos-migracao.

### 9.7 Fechamento

- [ ] Consolidar aprendizados em artefatos da fase.
- [ ] Confirmar que operacao principal nao depende do legado.
- [ ] Confirmar que o repo esta coerente para evolucao futura.
- [ ] Declarar encerramento da migracao arquitetural.

## 10. Primeiro Corte Tecnico Recomendado

Sequencia recomendada para a futura execucao:

1. fechar o plano de cutover com rollback;
2. trocar o ponto de entrada oficial do backend e validar baseline;
3. trocar o ponto de entrada oficial do frontend/BFF e validar baseline;
4. remover compatibilidades temporarias em ondas pequenas;
5. alinhar docker, scripts e documentacao no mesmo movimento final.

## 11. Perguntas que a Fase Precisa Responder

1. Qual e o momento exato em que o novo backend passa a ser a pilha oficial?
2. O que ainda resta de compatibilidade temporaria e quando cada item sai?
3. Quais arquivos e modulos do legado podem ser aposentados sem risco?
4. Como garantir rollback simples se o cutover falhar?
5. Qual o plano de manutencao depois que a migracao acabar?

## 12. Criterios de Saida

A Fase 9 so fecha quando:

- a operacao principal estiver na arquitetura nova;
- o legado critico estiver desativado ou removido;
- documentacao, scripts e ambiente estiverem alinhados;
- nao houver dependencia estrutural dos antigos arquivos monoliticos;
- existir plano claro de manutencao pos-migracao.

## 13. Encerramento do Ciclo

Esta fase encerra o ciclo de reescrita parcial guiada quando:

- o sistema deixa de depender do antigo centro monolitico;
- os contratos novos passam a ser a verdade oficial;
- o repo fica pronto para evolucao incremental sem medo arquitetural.

## 14. Status

Estado atual da fase:

- Status: `planned`
- Dono atual: `Codex + usuário`
- Documento mestre relacionado: [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md)

## 15. Proximo Passo Imediato

Planejamento da fase consolidado com os seguintes artefatos:

1. `phase-9-cutover-plan.md`
2. `phase-9-legacy-retirement.md`
3. `phase-9-docs-and-ops-alignment.md`
4. `phase-9-post-migration.md`

Proximo passo recomendado:

1. revisar o plano macro completo da reescrita;
2. escolher a primeira fase a sair de planejamento para execucao;
3. so depois iniciar codigo com autorizacao explicita do usuario.

## 16. Observacao Operacional

Este documento e um plano de execucao da fase, nao evidencia de que a fase ja foi executada.
