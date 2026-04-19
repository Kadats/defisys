# Fase 4: Nova Camada de Persistencia e Integracao Externa

## 1. Proposito

Este documento operacionaliza a Fase 4 definida em [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md).

Objetivo da fase:

- substituir acesso espalhado ao banco e aos provedores por adaptadores consistentes;
- separar leitura analitica de escrita transacional;
- transformar integracoes externas em gateways com contrato estavel;
- remover vazamento de infra para dentro da regra de negocio e da camada web.

Ao final desta fase, o backend deve depender de repositories e gateways explicitos, e nao mais de `psycopg2`, `pandas.read_sql` e chamadas externas espalhadas no codigo.

## 2. Resultado Esperado

Ao concluir a Fase 4, devemos ter:

- repositories claros para dados de mercado, predicoes, trades, summaries e eventos de paper trading;
- gateways concretos para provedores externos criticos;
- politicas padronizadas de timeout, retry, erro tipado e logging;
- migrations iniciais ou politica formal de schema management;
- adaptador unico do LLM com contrato completo de contexto, chamada, validacao, normalizacao e fallback;
- testes de integracao reais e isolados da nova camada de infra.

## 3. Regras da Fase

- Esta fase esta aberta apenas como planejamento.
- Nenhuma implementacao de codigo desta fase deve comecar sem autorizacao explicita do usuario.
- Nenhuma regra de negocio central deve nascer em repository ou gateway.
- Nenhuma rota HTTP deve acessar banco diretamente depois da execucao desta fase.
- Nenhum provider externo deve vazar resposta bruta para o dominio.
- Separacao entre leitura e escrita deve ser pensada desde o desenho, mesmo que a execucao venha em etapas.

## 3.1 Gate de Execucao

Antes de executar a Fase 4 no codigo, precisamos ter:

- Fase 3 executada ao menos para os fluxos centrais;
- commands e queries principais ja definidos e implementados;
- contratos de dominio e DTOs estaveis o suficiente para suportar adapters;
- confirmacao explicita do usuario para iniciar execucao.

## 4. Escopo

### 4.1 Banco

Planejar e depois executar:

- separacao de leitura analitica e escrita transacional;
- repositories claros para:
  - market data
  - predictions
  - trades
  - simulation summaries
  - paper trading events
- migrations formais ou mecanismo equivalente;
- naming e ownership das tabelas.

### 4.2 Provedores Externos

Encapsular integracoes com:

- Binance
- Blockchair
- Fear & Greed
- Deribit
- TheGraph
- RPC nodes
- LLM providers

Padronizar em todos:

- timeout
- retry
- erro tipado
- logging
- observabilidade

## 5. Dependencias de Entrada

Esta fase depende diretamente de:

- [phase-0-data-map.md](/home/luckstyle/repo/private/defisys-v1/phase-0-data-map.md)
- [phase-0-risks.md](/home/luckstyle/repo/private/defisys-v1/phase-0-risks.md)
- [phase-1-domain-contracts.md](/home/luckstyle/repo/private/defisys-v1/phase-1-domain-contracts.md)
- [phase-1-llm-contract.md](/home/luckstyle/repo/private/defisys-v1/phase-1-llm-contract.md)
- [phase-3.md](/home/luckstyle/repo/private/defisys-v1/phase-3.md)

## 6. Workstreams

### WS1. Persistencia

Definir a estrutura alvo de:

- repositories de leitura;
- repositories de escrita;
- mapeadores entre schema e contratos internos;
- politica de conexao, transacao e erro.

### WS2. Schema Management

Definir:

- como migrations vao funcionar;
- quais tabelas precisam de ownership explicito;
- quais tabelas podem ser reaproveitadas;
- quais naming inconsistencies precisam ser corrigidas.

### WS3. Gateways Externos

Definir adaptadores para:

- dados de mercado;
- dados auxiliares;
- RPC;
- LLM.

### WS4. Politicas de Erro e Observabilidade

Padronizar:

- timeout;
- retry;
- erro tipado;
- metadados de request;
- logs tecnicos;
- sinais para monitoramento.

### WS5. Adaptador do LLM

Consolidar em um unico adaptador:

- construcao de contexto;
- chamada ao provider;
- validacao estrutural da resposta;
- normalizacao;
- fallback;
- auditoria.

### WS6. Testes de Integracao

Planejar:

- testes reais e isolados dos repositories;
- testes reais e isolados dos gateways;
- estrategia de mocks controlados;
- ambientes de banco dedicados.

## 7. Entregaveis da Fase

Arquivos esperados ao final da Fase 4:

- `phase-4.md`
- `phase-4-repository-map.md`
- `phase-4-gateway-map.md`
- `phase-4-schema-plan.md`
- `phase-4-integration-test-plan.md`

Entregaveis de codigo esperados quando houver execucao:

- `backend/src/infrastructure/db/repositories/`
- `backend/src/infrastructure/db/mappers/`
- `backend/src/infrastructure/market_data/`
- `backend/src/infrastructure/ml/`
- `backend/src/infrastructure/llm/`
- `backend/src/infrastructure/rpc/`

## 8. Decisoes Tecnicas Recomendadas

- preferir `SQLAlchemy Core` ou camada leve equivalente, nao ORM pesado por padrao;
- manter `psycopg2` apenas se ficar completamente encapsulado;
- separar conexoes de leitura e escrita se isso fizer sentido depois;
- tratar o banco como detalhe de infraestrutura, nao como shape canonico do dominio;
- manter um adaptador unico do LLM, nao multiplos caminhos de integracao espalhados.

## 9. Checklist Operacional

### 9.1 Mapa de Repositories

- [ ] Definir repositories de market data.
- [ ] Definir repositories de predictions.
- [ ] Definir repositories de trades.
- [ ] Definir repositories de simulation summaries.
- [ ] Definir repositories de paper trading events.

### 9.2 Mapa de Gateways

- [ ] Definir gateway de Binance.
- [ ] Definir gateway de Blockchair.
- [ ] Definir gateway de Fear & Greed.
- [ ] Definir gateway de Deribit.
- [ ] Definir gateway de TheGraph.
- [ ] Definir gateway de RPC.
- [ ] Definir gateway unico de LLM.

### 9.3 Schema Management

- [ ] Definir estrategia de migrations.
- [ ] Definir ownership das tabelas principais.
- [ ] Registrar naming inconsistency e plano de compatibilidade.
- [ ] Definir o que pode ser reaproveitado sem mudanca.

### 9.4 Politicas Tecnicas

- [ ] Definir timeout padrao por provider.
- [ ] Definir retry policy por provider.
- [ ] Definir erro tipado por categoria.
- [ ] Definir padrao de logging tecnico.
- [ ] Definir padrao de observabilidade.

### 9.5 LLM Adapter

- [ ] Consolidar construcao de contexto.
- [ ] Consolidar chamada ao provider.
- [ ] Consolidar validacao estrutural.
- [ ] Consolidar normalizacao da resposta.
- [ ] Consolidar fallback.
- [ ] Consolidar auditoria.

### 9.6 Testes de Integracao

- [ ] Definir testes de repository.
- [ ] Definir testes de gateway.
- [ ] Definir fixtures e ambientes dedicados.
- [ ] Definir gate minimo para execucao segura da fase.

### 9.7 Fechamento

- [ ] Consolidar aprendizados em artefatos da fase.
- [ ] Confirmar que o dominio nao acessa banco diretamente.
- [ ] Confirmar que provedores externos nao vazam para o dominio.
- [ ] Declarar o corte minimo que destrava a Fase 5.

## 10. Primeiro Corte Tecnico Recomendado

Sequencia recomendada para a futura execucao:

1. criar repositories de `ml_predictions`, `trades` e `simulation_summary`;
2. criar mapeadores entre schema atual e contratos internos;
3. criar gateway unico do LLM;
4. criar testes de integracao desses componentes;
5. so depois expandir para os demais provedores e tabelas.

## 11. Perguntas que a Fase Precisa Responder

1. Qual o menor conjunto de repositories que elimina os maiores vazamentos atuais?
2. Quais provedores precisam de adaptador primeiro para destravar a Fase 5?
3. Como introduzir migrations sem quebrar a base atual?
4. Qual o ponto exato em que `psycopg2` pode ser considerado aceitavel ou precisa sair?
5. Como garantir que o adaptador do LLM nao recreie o acoplamento que estamos tentando remover?

## 12. Criterios de Saida

A Fase 4 so fecha quando:

- nenhuma regra de negocio acessar banco diretamente;
- nenhuma rota HTTP chamar `pandas.read_sql` diretamente;
- provedores externos deixarem de vazar para o dominio;
- repositories e gateways principais estiverem definidos e implementados;
- houver testes de integracao suficientes para sustentar a migracao.

## 13. Dependencias para a Fase 5

A Fase 5 depende diretamente desta fase para:

- tornar a API uma casca fina de verdade;
- remover leitura direta de banco da camada web;
- modularizar rotas e websockets sobre adapters estaveis.

## 14. Status

Estado atual da fase:

- Status: `planned`
- Dono atual: `Codex + usuário`
- Documento mestre relacionado: [plan.md](/home/luckstyle/repo/private/defisys-v1/plan.md)

## 15. Proximo Passo Imediato

Proximo passo recomendado ainda em modo planejamento:

1. criar `phase-4-repository-map.md`;
2. criar `phase-4-gateway-map.md`;
3. criar `phase-4-schema-plan.md`;
4. criar `phase-4-integration-test-plan.md`;
5. so depois abrir execucao quando a Fase 3 estiver realmente implementada.

## 16. Observacao Operacional

Este documento e um plano de execucao da fase, nao evidencia de que a fase ja foi executada.
