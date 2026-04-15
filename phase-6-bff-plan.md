# Fase 6: Plano do BFF e Proxies Internos

## 1. Objetivo

Este documento define o papel do BFF do Next.js na arquitetura-alvo da Fase 6.

## 2. Leitura Executiva

O BFF atual existe, mas hoje ele cumpre dois papeis misturados:

- proxy legitimo entre frontend e backend;
- camada que mascara falha real com payload “amigavel”.

Direcao recomendada:

- manter o BFF apenas onde ele agrega valor real;
- remover o uso dele como mecanismo de esconder indisponibilidade ou inventar saude do sistema.

## 3. BFF Atual Identificado

Arquivos atuais:

- `frontend/src/app/api/system/health/route.ts`
- `frontend/src/app/api/system/indicators/route.ts`
- `frontend/src/app/api/system/logs/route.ts`
- `frontend/src/app/api/sandbox/run/route.ts`

Configuracao relacionada:

- `frontend/next.config.ts`
  - rewrite para `/api/ws/:path*`

## 4. Funcoes Legitimamente Esperadas do BFF

O BFF pode continuar existindo para:

- concentrar URL do backend;
- normalizar headers e autenticacao quando existir;
- reduzir acoplamento do frontend com detalhes de ambiente;
- adaptar pequenos detalhes de contrato durante janela de compatibilidade;
- centralizar tratamento coerente de erro HTTP.

O BFF nao deve existir para:

- fabricar payload de sucesso quando o backend falhar;
- manter contrato paralelo indefinido;
- esconder `mock`, `degraded` ou `disabled`;
- reinterpretar semantica do backend sem controle.

## 5. Diagnostico dos Proxies Atuais

## 5.1 `GET /api/system/health`

Problema atual:

- em falha, devolve estrutura offline sintetica;
- o consumidor pode tratar isso como resposta valida de health.

Risco:

- mascara indisponibilidade real;
- mistura erro de rede com snapshot legitimo de saude.

Direcao:

- devolver erro tipado ou resposta degradada explicitamente marcada;
- nao inventar shape de sucesso sem `source_status`.

## 5.2 `GET /api/system/indicators`

Problema atual:

- em falha, devolve RSI/FG/Regime padrao.

Risco:

- indicador parece real quando nao e;
- UI perde capacidade de distinguir dado offline de mercado sideways real.

Direcao:

- devolver erro ou payload com `source_status = degraded`;
- nunca confundir fallback com dado real.

## 5.3 `GET /api/system/logs`

Problema atual:

- em falha, devolve array com mensagem de erro como se fosse log.

Risco:

- mistura erro tecnico com dado de dominio da tela;
- UI precisa inferir semantica pelo conteudo do texto.

Direcao:

- devolver erro padrao ou envelope tecnico explicito;
- nao usar string de erro como se fosse linha de log.

## 5.4 `POST /api/sandbox/run`

Problema atual:

- ja atua como proxy simples;
- em erro, devolve mensagem amigavel.

Leitura:

- e o menos problematico dos BFFs atuais;
- ainda precisa de semantica clara de laboratorio.

## 6. Politica Recomendada para o BFF da Fase 6

## 6.1 HTTP

- o BFF deve ser fino;
- o BFF deve delegar para a API canonica da Fase 5;
- quando adaptar payload, isso deve ser explicitamente temporario;
- toda resposta adaptada deve preservar `source_status`, `schema_version` e `warnings` quando existirem.

## 6.2 Erro

- erro de backend deve continuar sendo erro para o frontend;
- se houver resposta degradada, ela precisa ser marcada como degradada;
- nao usar `200` com payload inventado para esconder falha estrutural.

## 6.3 WebSocket

Leitura atual:

- o hook `useWebSocket` conecta direto a `ws://<host>:8000`;
- o rewrite do Next existe, mas nao e o contrato principal do hook atual.

Direcao recomendada:

- escolher um caminho oficial:
  - ou WebSocket passa pelo dominio do frontend via proxy/rewrite coerente;
  - ou a conexao direta ao backend vira caminho oficial documentado;
- a escolha precisa ser unica e documentada.

## 7. Modelo Alvo do BFF

Direcao recomendada:

- BFF so para HTTP;
- WebSocket com caminho oficial unico e documentado;
- adaptadores de compatibilidade isolados;
- qualquer regra de negocio continua fora do BFF.

## 8. Prioridade de Reconciliacao

Prioridade P0:

- `system/health`
- `system/indicators`
- `system/logs`

Prioridade P1:

- `sandbox/run`
- alinhamento do caminho oficial de WebSocket

Prioridade P2:

- limpeza de qualquer proxy residual da arquitetura antiga

## 9. Decisoes que a Fase Precisa Fechar

1. O BFF continua existindo para HTTP?
2. Como o frontend recebe erro sem perder UX, mas sem mentir sobre o estado do sistema?
3. O caminho oficial de WebSocket sera proxy via Next ou conexao direta documentada?
4. Quais adaptacoes de payload vao continuar temporariamente durante a Fase 6?
5. Como remover fallback que hoje se passa por dado real?

## 10. Status do Entregavel

- status: `draft-initial`
- pronto para orientar a reconciliacao do BFF na Fase 6
- depende da execucao da Fase 5 para consolidar os contratos finais da API
