# Fase 0: Inventario de Interfaces

## 1. Objetivo

Mapear a superficie publica atual do sistema para proteger a migracao contra quebra acidental de contrato.

Este inventario cobre:

- rotas FastAPI do backend;
- webSockets do backend;
- proxies/BFF do frontend;
- consumidores conhecidos no frontend;
- inconsistencias relevantes entre docs e implementacao.

## 2. Leitura Executiva

Estado atual da interface do sistema:

- o backend concentra a maior parte da superficie publica em `backend/src/api.py`;
- coexistem rotas em `/api/*` e `/api/v1/*`;
- o frontend usa tanto proxies HTTP internos quanto conexao WebSocket direta para o backend;
- parte do comportamento de tempo real ainda e mockado;
- existe desvio entre o que o README promete e o que a API realmente expoe hoje.

## 3. Rotas HTTP do Backend

## 3.1 Market Data

### `GET /api/history`

- finalidade: retornar historico OHLCV direto da tabela `btcusdt_4h_klines`;
- observacao:
  - usa conexao direta com banco e `pandas.read_sql` dentro da camada web;
  - contrato simples, mas acoplado a tabela fisica;
- risco de migracao: medio.

### `GET /api/v1/chart_data`

- finalidade: retornar velas historicas para graficos, com filtro opcional por data;
- observacao:
  - depende de `get_data_from_db`;
  - parece ser a rota mais alinhada ao frontend moderno do que `/api/history`;
- risco de migracao: alto, porque alimenta visualizacao.

### `GET /api/v1/market_analysis`

- finalidade: analise historica anual de mercado;
- observacao:
  - usa historico completo;
  - e uma rota analitica, nao operacional;
- risco de migracao: medio.

## 3.2 Simulation / Backtest

### `GET /api/simulation`

- finalidade: retornar KPIs, trades e summary da simulacao;
- observacao:
  - tenta combinar calculo em memoria com summary oficial do banco;
  - ja contem fallback de payload para evitar erro duro;
- risco de migracao: alto.

### `POST /api/simulation/run`

- finalidade: iniciar simulacao em background;
- observacao:
  - valida se existe predicao no banco antes de rodar;
  - depende de flags globais e de `asyncio.create_task`;
- risco de migracao: muito alto.

### `GET /api/simulation/status`

- finalidade: informar se a simulacao esta rodando e se ha resultado;
- observacao:
  - mistura flag global com leitura do banco;
- risco de migracao: medio.

### `GET /api/simulation/summary`

- finalidade: retornar resumo de tesourarias isoladas;
- observacao:
  - e uma visao derivada do `simulation_summary`;
  - util para UI e auditoria;
- risco de migracao: alto.

### `GET /api/v1/summary`

- finalidade: retornar resumo de backtest para dashboard legado;
- observacao:
  - chama `run_trading_system()` se nao houver summary oficial;
  - mistura comportamento de consulta com execucao;
- risco de migracao: muito alto.

### `GET /api/v1/trade_history`

- finalidade: retornar log detalhado de transacoes;
- observacao:
  - pode disparar `run_trading_system()` novamente;
  - reexecuta para montar historico fresco;
- risco de migracao: muito alto.

### `GET /api/v1/backtest_period`

- finalidade: retornar datas do ultimo backtest;
- observacao:
  - depende de cache ou executa o sistema;
- risco de migracao: alto.

### `GET /api/v1/positions`

- finalidade: retornar posicoes abertas e fechadas;
- observacao:
  - contrato relativamente limpo;
  - bom candidato a query separada na nova arquitetura;
- risco de migracao: medio.

## 3.3 Model / ML

### `POST /api/model/train`

- finalidade: treinar o modelo de ML e salvar predicoes;
- observacao:
  - chama pipeline sincrono em threadpool;
  - mistura comando operacional com resposta HTTP amigavel;
- risco de migracao: muito alto.

## 3.4 System / Control Center

### `GET /api/system/health`

- finalidade: retornar health dos RPCs;
- observacao:
  - hoje responde via `rpc_manager.get_all_health()`;
- risco de migracao: medio.

### `GET /api/system/logs`

- finalidade: retornar ultimas linhas de log persistido;
- observacao:
  - leitura direta de arquivo;
  - faz parte do System Pulse;
- risco de migracao: medio.

### `GET /api/system/indicators`

- finalidade: retornar indicadores em tempo real para o dashboard;
- observacao:
  - se base vazia, responde com zeros e regime unknown;
- risco de migracao: alto.

### `POST /api/sandbox/run`

- finalidade: disparar simulacao do Sandbox Lab;
- observacao:
  - hoje devolve simulacao fake controlada por payload;
  - e claramente um endpoint de laboratorio/mock;
- risco de migracao: medio.

## 4. WebSockets do Backend

### `WS /ws/logs`

- finalidade: stream generico de logs;
- status funcional: aparentemente real, mas simples;
- risco de migracao: medio.

### `WS /api/ws/pulse`

- finalidade: alias do stream de logs para o frontend System Pulse;
- status funcional: real, conectado ao `manager`;
- risco de migracao: alto, porque a UI depende dele.

### `WS /api/ws/ticker`

- finalidade: stream de ticker para o War Room;
- status funcional: mockado;
- observacao:
  - envia preco sintetico com `np.random.normal`;
  - ainda nao representa runtime real do motor;
- risco de migracao: alto.

## 5. Proxies / BFF do Frontend

Rotas internas identificadas em `frontend/src/app/api`:

### `GET /api/system/health`

- proxy para backend `/system/health`;
- fallback local do Next.js quando backend falha;
- consumidor conhecido:
  - `frontend/src/components/TickerHeader.tsx`

### `GET /api/system/indicators`

- proxy para backend `/system/indicators`;
- fallback local com payload offline;
- consumidor conhecido:
  - `frontend/src/components/IndicatorWidget.tsx`

### `GET /api/system/logs`

- proxy para backend `/system/logs`;
- fallback local com mensagem de erro;
- consumidor conhecido:
  - `frontend/src/app/dashboard/pulse/page.tsx`

### `POST /api/sandbox/run`

- proxy para backend `/sandbox/run`;
- fallback local com erro amigavel;
- consumidor conhecido:
  - `frontend/src/app/dashboard/sandbox/page.tsx`

## 6. Consumidores Diretos no Frontend

### Consumo via WebSocket direto

- `frontend/src/app/dashboard/page.tsx`
  - usa `useWebSocket('/api/ws/ticker')`
- `frontend/src/components/TickerHeader.tsx`
  - usa `useWebSocket('/api/ws/ticker')`
- `frontend/src/app/dashboard/pulse/page.tsx`
  - usa `useWebSocket('/api/ws/pulse')`

### Consumo via fetch no BFF

- `frontend/src/components/IndicatorWidget.tsx`
  - `/api/system/indicators`
- `frontend/src/components/TickerHeader.tsx`
  - `/api/system/health`
- `frontend/src/app/dashboard/pulse/page.tsx`
  - `/api/system/logs`
- `frontend/src/app/dashboard/sandbox/page.tsx`
  - `/api/sandbox/run`

## 7. Classificacao por Dominio Funcional

## 7.1 System / Control Center

- `GET /api/system/health`
- `GET /api/system/logs`
- `GET /api/system/indicators`
- `POST /api/sandbox/run`
- `WS /ws/logs`
- `WS /api/ws/pulse`
- `WS /api/ws/ticker`

## 7.2 Market

- `GET /api/history`
- `GET /api/v1/chart_data`

## 7.3 Model

- `POST /api/model/train`

## 7.4 Simulation

- `GET /api/simulation`
- `POST /api/simulation/run`
- `GET /api/simulation/status`
- `GET /api/simulation/summary`
- `GET /api/v1/summary`
- `GET /api/v1/trade_history`
- `GET /api/v1/backtest_period`
- `GET /api/v1/positions`

## 7.5 Analytics

- `GET /api/v1/market_analysis`

Observacao:

- no estado atual, simulation e analytics ainda vivem muito proximos;
- a classificacao acima e funcional, nao arquitetural.

## 8. Bootstrap, Startup e Scripts Relevantes

## 8.1 Bootstrap automatico observado

- `backend/src/api.py`
  - `@app.on_event("startup")`
  - ativa `startup_sync_market_data()`
  - executa `sync_market_data()` em threadpool

## 8.2 Bootstrap manual / legado

- `backend/src/main.py`
  - quando executado como script, chama `run_trading_system()`
  - e um caminho manual all-in-one, nao o bootstrap normal da API

## 8.3 Scripts e pontos de operacao relevantes

- `make run-api`
- `make up`
- `make up-test`
- `./setup_cloud.sh`

Leitura pratica:

- o startup real da aplicacao hoje ja dispara comportamento de coleta;
- o caminho CLI manual ainda existe e preserva o fluxo monolitico legado.

## 9. Riscos de Interface para a Reescrita

### Risco A. Mistura de namespaces

Hoje coexistem:

- `/api/*`
- `/api/v1/*`

Isto sugere duas eras de contrato convivendo no mesmo arquivo. A reescrita deve decidir:

- padronizar tudo sob versao unica;
- ou manter compatibilidade temporaria com alias bem definidos.

### Risco B. Rotas de consulta com side effect

Algumas rotas de leitura podem disparar execucao do sistema quando nao ha cache ou summary. Isso e um risco forte de design e de migracao.

Rotas mais sensiveis:

- `/api/v1/summary`
- `/api/v1/trade_history`
- `/api/v1/backtest_period`

### Risco C. WebSocket de ticker mockado

O frontend atual parece “live”, mas o ticker ainda e sintetico no backend. A reescrita precisa decidir explicitamente se:

- mantem mock visivel;
- troca por feed real;
- ou desabilita o modulo ate haver runtime real.

### Risco D. Fallbacks escondem falha real

No frontend, varios proxies devolvem payload de fallback. Isso suaviza UX, mas mascara estado real do sistema.

### Risco E. README divergente

O README menciona rotas e modulos que nao refletem exatamente a superficie atual. Isso aumenta o risco de migracao por expectativa errada.

## 10. Divergencias Encontradas

### Divergencia 1. README versus implementacao

O README destaca, entre outras, estas rotas:

- `POST /api/data/sync`
- `GET /api/simulation/summary`

Na implementacao observada:

- `POST /api/data/sync` nao apareceu na superficie atual mapeada;
- `GET /api/simulation/summary` existe;
- ha tambem varias rotas `/api/v1/*` que nao estao refletidas na narrativa principal do README.

### Divergencia 2. “Tempo real” versus mock

O frontend vende War Room e System Pulse em tempo real, mas o ticker hoje ainda e gerado artificialmente.

## 11. Recomendacoes para Fase 1 e Fase 5

### Para Fase 1

- tratar cada rota atual como adaptador, nao como contrato definitivo;
- extrair contratos de dominio sem copiar a mistura atual de namespaces.

### Para Fase 5

- padronizar namespace da API;
- separar queries puras de comandos operacionais;
- proibir endpoint GET que dispara execucao pesada implicitamente;
- tornar estado mockado explicitamente visivel no contrato.

## 12. Status do Entregavel

- status: `draft-initial`
- pronto para uso como baseline de interfaces da Fase 0
- ainda pode ser enriquecido com exemplos de payload em iteracao futura
