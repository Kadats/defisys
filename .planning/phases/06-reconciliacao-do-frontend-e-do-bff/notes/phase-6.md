# Fase 6: Reconciliacao do Frontend e do BFF

## 1. Proposito

Este documento operacionaliza a Fase 6 definida em [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md).

Objetivo da fase:

- alinhar o frontend ao backend real;
- reduzir ruido arquitetural entre UI, BFF e API;
- explicitar o que e dado real, derivado, mockado ou placeholder;
- remover dependencias do frontend em contratos improvisados ou fallbacks escondidos;
- consolidar uma superficie oficial para dashboard, pulse, sandbox e fluxos correlatos.

Ao final desta fase, o frontend deve consumir contratos estaveis e semanticamente claros, sem depender de comportamento acidental do legado.

## 2. Resultado Esperado

Ao concluir a Fase 6, devemos ter:

- definicao oficial do frontend principal em uso;
- BFF/proxies alinhados com a API canonica;
- dashboard e paginas operacionais consumindo contratos consistentes;
- placeholders e mocks visiveis, controlados ou removidos;
- politica clara para login, pulse, sandbox e ticker header;
- documentacao do frontend atualizada e coerente com a arquitetura real.

## 3. Regras da Fase

- Esta fase esta aberta apenas como planejamento.
- Nenhuma implementacao de codigo desta fase deve comecar sem autorizacao explicita do usuario.
- O frontend nao deve mascarar falha do backend como se fosse dado real.
- BFF e proxies internos nao devem virar segunda API paralela com regras proprias.
- Placeholder visual so pode existir se estiver identificado como temporario.
- O frontend deve refletir o estado operacional real dos dados que consome.
- Nenhuma pagina principal deve depender de endpoint improvisado ou mock oculto.

## 3.1 Gate de Execucao

Antes de executar a Fase 6 no codigo, precisamos ter:

- Fase 5 executada ao menos para as rotas e streams centrais;
- contratos HTTP e WebSocket estaveis para os fluxos principais;
- estrategia de compatibilidade da Fase 5 aprovada;
- entendimento fechado sobre qual frontend e oficial na arquitetura-alvo;
- confirmacao explicita do usuario para iniciar execucao.

## 4. Escopo

Incluido nesta fase:

- consolidacao do frontend principal e do papel do BFF;
- revisao de proxies internos;
- alinhamento das telas de dashboard, pulse, sandbox e header com a API nova;
- definicao do comportamento de login e estados vazios;
- remocao ou explicitacao de placeholders e mocks;
- limpeza de restos de arquitetura anterior;
- atualizacao da documentacao do frontend.

Fora do escopo desta fase:

- redesign visual completo;
- troca de framework frontend por impulso;
- reescrita do backend;
- criacao de novos produtos ou dashboards paralelos;
- adicao de novos fluxos antes de estabilizar os existentes.

## 5. Dependencias de Entrada

Esta fase depende diretamente de:

- [phase-0-endpoints.md](/home/luckstyle/repo/private/defisys-v1/phase-0-endpoints.md)
- [phase-0-risks.md](/home/luckstyle/repo/private/defisys-v1/phase-0-risks.md)
- [phase-5.md](/home/luckstyle/repo/private/defisys-v1/phase-5.md)
- [phase-5-route-map.md](/home/luckstyle/repo/private/defisys-v1/phase-5-route-map.md)
- [phase-5-schema-plan.md](/home/luckstyle/repo/private/defisys-v1/phase-5-schema-plan.md)
- [phase-5-websocket-plan.md](/home/luckstyle/repo/private/defisys-v1/phase-5-websocket-plan.md)
- [phase-5-compatibility-plan.md](/home/luckstyle/repo/private/defisys-v1/phase-5-compatibility-plan.md)

## 6. Workstreams

### WS1. Frontend Canonico

Definir e registrar:

- qual frontend e a interface oficial do produto;
- quais restos de stack anterior devem ser arquivados, removidos ou ignorados;
- quais docs e scripts ainda apontam para arquitetura antiga;
- qual o papel do BFF interno na arquitetura final.

### WS2. Reconciliacao do Dashboard

Planejar:

- contratos finais consumidos pelo dashboard principal;
- estado do ticker header;
- estado dos indicadores;
- comportamento de loading, empty state e degradacao;
- estrategia para remover dependencia de payload composto legado.

### WS3. Pulse e Observabilidade

Planejar:

- integracao da pagina de pulse com `logs` e `pulse` novos;
- tratamento de stream indisponivel, degradado ou desconectado;
- eliminacao de alias opacos entre log stream e pulse;
- clareza visual sobre origem e status do dado.

### WS4. Sandbox e Fluxos de Laboratorio

Planejar:

- se o sandbox continua existindo;
- como ele deve ser apresentado se continuar fake ou parcial;
- como evitar que laboratorio pareca comportamento produtivo;
- qual o contrato visual e tecnico do sandbox apos a Fase 6.

### WS5. Login e Fluxos Incompletos

Definir:

- se login atual e placeholder, stub ou fluxo real;
- qual o destino de telas ou fluxos inacabados;
- como tratar autenticacao inexistente ou parcial sem vender integridade falsa ao usuario.

### WS6. Politica de Mock, Placeholder e Fallback

Definir:

- o que pode continuar como placeholder temporario;
- o que precisa virar estado explicito de degradacao;
- o que deve ser removido;
- como a UI comunica `real`, `derived`, `mock`, `degraded` e `disabled`.

### WS7. Documentacao e Higiene de Stack

Planejar:

- atualizacao da documentacao do frontend;
- limpeza de referencias antigas de stack;
- consolidacao de comandos e caminho oficial de desenvolvimento;
- alinhamento entre README e arquitetura real.

## 7. Entregaveis da Fase

Arquivos esperados ao final da Fase 6:

- `phase-6.md`
- `phase-6-frontend-map.md`
- `phase-6-bff-plan.md`
- `phase-6-ui-state-policy.md`
- `phase-6-compatibility-matrix.md`

Entregaveis de codigo esperados quando houver execucao:

- frontend reconciliado com os contratos da Fase 5;
- proxies/BFF internos reduzidos e alinhados;
- remocao de fallbacks enganosos;
- documentacao do frontend atualizada.

## 8. Decisoes Tecnicas Recomendadas

- assumir um frontend oficial e documentar isso sem ambiguidade;
- manter BFF apenas onde ele agrega adaptacao legitima, nao como duplicacao do backend;
- tratar `source_status` e estado operacional como parte do contrato de UI;
- remover fallback que simula saude do sistema quando o backend falha;
- separar claramente dado operacional de placeholder de UX;
- so manter mock onde ele for deliberado e visivel.

## 9. Checklist Operacional

### 9.1 Frontend Canonico

- [ ] Definir frontend oficial do produto.
- [ ] Registrar restos de arquitetura antiga.
- [ ] Registrar impacto disso em docs e scripts.
- [ ] Definir papel final do BFF.

### 9.2 Dashboard

- [ ] Mapear contratos consumidos pelo dashboard principal.
- [ ] Mapear dependencias de ticker e indicadores.
- [ ] Definir estado vazio e degradado.
- [ ] Definir o que sai do payload legado composto.

### 9.3 Pulse

- [ ] Mapear consumo atual de logs e pulse.
- [ ] Definir contrato final da pagina de pulse.
- [ ] Definir estados de desconexao, degradacao e mock.
- [ ] Eliminar alias opaco entre streams.

### 9.4 Sandbox

- [ ] Decidir se sandbox continua.
- [ ] Definir contrato visual e tecnico do sandbox.
- [ ] Definir como identificar laboratorio/mock.
- [ ] Definir criterio de remocao ou consolidacao.

### 9.5 Login e Fluxos Incompletos

- [ ] Mapear fluxo atual de login.
- [ ] Classificar o que e real, parcial ou placeholder.
- [ ] Definir destino dos fluxos incompletos.
- [ ] Definir regra de apresentacao segura para estados nao implementados.

### 9.6 Politica de UI State

- [ ] Definir tratamento visual para `real`.
- [ ] Definir tratamento visual para `derived`.
- [ ] Definir tratamento visual para `mock`.
- [ ] Definir tratamento visual para `degraded`.
- [ ] Definir tratamento visual para `disabled`.

### 9.7 Documentacao

- [ ] Atualizar narrativa do frontend no plano.
- [ ] Alinhar README com a arquitetura real.
- [ ] Definir comandos oficiais de desenvolvimento.
- [ ] Registrar o que deve ser aposentado como stack anterior.

### 9.8 Fechamento

- [ ] Consolidar aprendizados em artefatos da fase.
- [ ] Confirmar que frontend e backend falam o mesmo idioma.
- [ ] Confirmar que nenhum modulo principal depende de mock oculto.
- [ ] Declarar o corte minimo que destrava a Fase 7.

## 10. Primeiro Corte Tecnico Recomendado

Sequencia recomendada para a futura execucao:

1. declarar oficialmente o frontend canonico e o papel do BFF;
2. alinhar `health`, `indicators`, `logs` e `pulse` aos contratos da Fase 5;
3. tornar o estado do `ticker` visivel na UI;
4. revisar sandbox e login, removendo apresentacao enganosa;
5. so depois limpar restos de arquitetura anterior e consolidar a documentacao.

## 11. Perguntas que a Fase Precisa Responder

1. Qual frontend e oficialmente o produto em evolucao?
2. O BFF e necessario como adaptador legitimo ou hoje so mascara inconsistencias do backend?
3. Quais telas ainda vendem dado fake como se fosse estado real do sistema?
4. O que precisa continuar como placeholder temporario e o que ja deve ser removido?
5. Qual o menor corte de reconciliacao que ja elimina as maiores ambiguidades do painel?

## 12. Criterios de Saida

A Fase 6 so fecha quando:

- houver frontend oficial claramente definido;
- dashboard, pulse e fluxos principais consumirem contratos consistentes;
- estados de mock, degradacao e indisponibilidade estiverem explicitos;
- BFF e proxies internos nao mascararem falhas do backend;
- nenhum modulo principal depender de endpoint improvisado ou mock oculto.

## 13. Dependencias para a Fase 7

A Fase 7 depende diretamente desta fase para:

- validar fluxos reais de UI e BFF com contratos estabilizados;
- medir regressao funcional ponta a ponta;
- reduzir testes contra comportamento improvisado do frontend;
- transformar o comportamento reconciliado em baseline verificavel.

## 14. Status

Estado atual da fase:

- Status: `planned`
- Dono atual: `Codex + usuário`
- Documento mestre relacionado: [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md)

## 15. Proximo Passo Imediato

Planejamento da fase consolidado com os seguintes artefatos:

1. `phase-6-frontend-map.md`
2. `phase-6-bff-plan.md`
3. `phase-6-ui-state-policy.md`
4. `phase-6-compatibility-matrix.md`

Proximo passo recomendado:

1. abrir o planejamento da Fase 7;
2. so depois iniciar execucao da Fase 6 quando a Fase 5 estiver realmente implementada.

## 16. Observacao Operacional

Este documento e um plano de execucao da fase, nao evidencia de que a fase ja foi executada.
