# Fase 6: Mapa do Frontend Atual

## 1. Objetivo

Este documento registra o estado real do frontend para orientar a reconciliacao da Fase 6.

## 2. Leitura Executiva

Conclusao principal:

- o frontend oficial em uso hoje e o `Next.js` em `frontend/`;
- existe um `frontend-vue-backup/` que e legado e nao deve ser tratado como interface canonica;
- a UI atual mistura componentes reais de observabilidade com placeholders visuais, fallbacks amigaveis e mock oculto;
- o BFF do Next.js hoje mascara parte das falhas reais do backend.

## 3. Estrutura Canonica Identificada

Frontend principal:

- `frontend/`

Sinais concretos:

- `frontend/package.json`
- `frontend/next.config.ts`
- `frontend/src/app/`
- `frontend/src/components/`
- `frontend/src/app/api/`

Legado identificado:

- `frontend-vue-backup/`

Direcao recomendada:

- assumir `frontend/` como unico frontend oficial;
- tratar `frontend-vue-backup/` como artefato de transicao ou arquivo historico, nao como stack viva do produto.

## 4. Mapa de Rotas de UI

Rotas identificadas no App Router:

- `/`
  - `frontend/src/app/page.tsx`
- `/login`
  - `frontend/src/app/login/page.tsx`
- `/dashboard`
  - `frontend/src/app/dashboard/page.tsx`
- `/dashboard/pulse`
  - `frontend/src/app/dashboard/pulse/page.tsx`
- `/dashboard/sandbox`
  - `frontend/src/app/dashboard/sandbox/page.tsx`

Layout relacionado:

- `frontend/src/app/layout.tsx`
- `frontend/src/app/dashboard/layout.tsx`

## 5. Componentes e Hooks Criticos

Componentes principais identificados:

- `frontend/src/components/TickerHeader.tsx`
- `frontend/src/components/IndicatorWidget.tsx`

Hook central:

- `frontend/src/hooks/useWebSocket.ts`

Leitura pratica:

- `TickerHeader` depende de WebSocket e de BFF de health;
- `IndicatorWidget` depende do BFF de indicators;
- `System Pulse` depende de WebSocket e BFF de logs;
- `Sandbox` depende do BFF de simulacao;
- `Dashboard` usa o estado de conexao do ticker como sinal global de “system online”.

## 6. BFF e Proxies Atuais

Rotas internas identificadas:

- `frontend/src/app/api/system/health/route.ts`
- `frontend/src/app/api/system/indicators/route.ts`
- `frontend/src/app/api/system/logs/route.ts`
- `frontend/src/app/api/sandbox/run/route.ts`

Leitura pratica:

- o frontend usa BFF para HTTP;
- para WebSocket, ele nao usa o rewrite do Next como contrato principal do hook;
- o hook monta conexao direta para `ws://<host>:8000`.

Implicacao:

- existe assimetria entre o caminho HTTP e o caminho WebSocket;
- isso precisa ser reconciliado na Fase 6.

## 7. Estados Reais, Placeholders e Mock por Area

## 7.1 Login

Arquivo:

- `frontend/src/app/login/page.tsx`

Estado atual:

- placeholder explicito;
- menciona “Placeholder for NextAuth login form”.

Classificacao:

- `placeholder`

## 7.2 Dashboard

Arquivo:

- `frontend/src/app/dashboard/page.tsx`

Estado atual:

- usa `useWebSocket('/api/ws/ticker')` para status online/offline;
- possui blocos visuais ainda placeholder:
  - “Initializing Neural Engine...”
  - terminal visual estatico;
  - Risk Protocol com numeros fixos.

Classificacao:

- misto de `derived`, `placeholder` e mock visual

## 7.3 Ticker Header

Arquivo:

- `frontend/src/components/TickerHeader.tsx`

Estado atual:

- consome `ticker` por WebSocket;
- chama `/api/system/health`;
- usa fallback local para RPC offline;
- usa valores default para BTC e ETH;
- simula ETH como `~0.052 BTC` quando nao existe dado.

Classificacao:

- mistura `mock`, `degraded` e `placeholder`

## 7.4 Indicator Widget

Arquivo:

- `frontend/src/components/IndicatorWidget.tsx`

Estado atual:

- chama `/api/system/indicators`;
- se falhar, mantem defaults locais:
  - RSI `48.5`
  - Fear & Greed `42`
  - regime `sideways`

Classificacao:

- `degraded` com apresentacao ambigua

## 7.5 System Pulse

Arquivo:

- `frontend/src/app/dashboard/pulse/page.tsx`

Estado atual:

- usa WebSocket para `/api/ws/pulse`;
- carrega logs iniciais via `/api/system/logs`;
- exibe console funcional, mas o status WS hoje nao diferencia stream real, degradado ou alias.

Classificacao:

- mais proximo de `real`, mas com semantica incompleta

## 7.6 Sandbox

Arquivo:

- `frontend/src/app/dashboard/sandbox/page.tsx`

Estado atual:

- chama `/api/sandbox/run`;
- UI e relativamente completa;
- backend atual do sandbox e fake/laboratorial.

Classificacao:

- `mock` ou `laboratorio`, mas hoje com visual mais “real” do que deveria

## 8. Inconsistencias Relevantes

### Inconsistencia A. README versus realidade de dados

O `frontend/README.md` fala em “Real-time monitoring” e “institutional-grade dashboard”, mas:

- ticker ainda pode ser mockado;
- indicadores tem fallback local;
- login e placeholder;
- partes do dashboard ainda sao essencialmente cenograficas.

### Inconsistencia B. WebSocket sem metadado operacional

O frontend hoje sabe apenas se conectou ou nao.

Ele nao sabe claramente se:

- o stream e real;
- o stream e mockado;
- o stream esta degradado;
- o stream e apenas alias de outro feed.

### Inconsistencia C. BFF mascarando falha

Os route handlers HTTP do Next devolvem payloads “amigaveis” quando o backend falha.

Isso protege UX, mas mascara o estado real do sistema.

## 9. Decisoes Recomendadas para a Fase 6

- declarar `frontend/` como frontend oficial;
- tratar `frontend-vue-backup/` como legado arquivado;
- revisar `TickerHeader` como prioridade alta;
- revisar `IndicatorWidget` para expor `source_status`;
- manter `Pulse` como area mais proxima do runtime real;
- reclassificar `Sandbox` explicitamente como laboratorio;
- tratar `login` como fluxo ausente, nao como feature pronta.

## 10. Status do Entregavel

- status: `draft-initial`
- pronto para orientar a reconciliacao do frontend na Fase 6
- pode ser enriquecido com referencias adicionais de documentacao e rotas quando a execucao da fase comecar
