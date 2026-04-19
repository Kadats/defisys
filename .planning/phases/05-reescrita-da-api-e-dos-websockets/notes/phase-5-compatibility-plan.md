# Fase 5: Plano de Compatibilidade e Deprecacao

## 1. Objetivo

Este documento define a politica de compatibilidade da Fase 5.

A meta aqui e permitir a migracao da API e dos WebSockets sem:

- quebrar consumidores conhecidos de forma acidental;
- manter contratos legados indefinidamente;
- esconder degradacoes sob aliases permanentes;
- deixar a convivencia entre antigo e novo sem dono claro.

## 2. Principios de Compatibilidade

- compatibilidade existe para transicao, nao como arquitetura final;
- alias legado deve apontar para a implementacao nova, nao para logica paralela;
- toda compatibilidade precisa de criterio objetivo de remocao;
- contrato legado com side effect nao deve ser perpetuado;
- quando um comportamento for incorreto, a compatibilidade deve preservar acesso, nao o erro de arquitetura;
- mock, fallback e degradacao precisam ficar explicitos no contrato.

## 3. Tipos de Compatibilidade Permitidos

## 3.1 Alias de Rota

Uso permitido quando:

- existe consumidor real mapeado;
- a diferenca e principalmente de caminho;
- o payload pode ser servido pelo contrato novo com adaptacao pequena.

Regra:

- alias deve delegar para o novo caso de uso ou novo handler;
- o legado nao deve manter fluxo proprio depois da migracao.

## 3.2 Adaptador de Payload

Uso permitido quando:

- o frontend ainda depende de shape antigo;
- o endpoint novo ja existe, mas a UI ainda nao foi reconciliada.

Regra:

- adaptador deve ser temporario;
- adaptador deve ficar isolado na camada de interface;
- dominio e aplicacao nao conhecem shape legado.

## 3.3 Compatibilidade de WebSocket

Uso permitido quando:

- a UI ainda consome stream antigo;
- o novo contrato de evento exige migracao coordenada.

Regra:

- stream antigo deve receber metadata suficiente para nao mascarar mock/degradacao;
- o stream novo deve ser considerado a referencia canonica.

## 4. Consumidores Conhecidos que Guiam a Compatibilidade

Consumidores HTTP/BFF mapeados:

- `frontend/src/components/TickerHeader.tsx`
- `frontend/src/components/IndicatorWidget.tsx`
- `frontend/src/app/dashboard/pulse/page.tsx`
- `frontend/src/app/dashboard/sandbox/page.tsx`

Consumidores WebSocket mapeados:

- `frontend/src/app/dashboard/page.tsx`
- `frontend/src/components/TickerHeader.tsx`
- `frontend/src/app/dashboard/pulse/page.tsx`

Implicacao:

- qualquer remocao de compatibilidade deve considerar explicitamente esses consumidores;
- endpoint ou stream sem consumidor mapeado pode ter janela de compatibilidade mais curta.

## 5. Matriz de Compatibilidade Planejada

## 5.1 HTTP

### `GET /api/system/health`

- contrato novo alvo:
  - `GET /api/v1/system/health`
- estrategia:
  - manter alias temporario
- tipo de compatibilidade:
  - alias de rota
- criterio de remocao:
  - BFF e consumidores migrarem para a rota versionada

### `GET /api/system/logs`

- contrato novo alvo:
  - `GET /api/v1/system/logs`
- estrategia:
  - manter alias temporario
- tipo de compatibilidade:
  - alias de rota
- criterio de remocao:
  - pulse page e BFF migrarem para o namespace novo

### `GET /api/system/indicators`

- contrato novo alvo:
  - `GET /api/v1/system/indicators`
- estrategia:
  - manter alias temporario com adaptacao de payload se necessario
- tipo de compatibilidade:
  - alias de rota
  - adaptador de payload
- criterio de remocao:
  - consumidores aceitarem `source_status` e contrato novo completo

### `POST /api/sandbox/run`

- contrato novo alvo:
  - `POST /api/v1/control-center/sandbox/run`
- estrategia:
  - manter apenas se a UI ainda consumir
- tipo de compatibilidade:
  - alias de rota
- criterio de remocao:
  - rota nova absorver o fluxo ou o sandbox ser aposentado

### `GET /api/history`

- contrato novo alvo:
  - `GET /api/v1/market/chart-data`
- estrategia:
  - preferir aposentadoria
- tipo de compatibilidade:
  - alias curto, se necessario
- criterio de remocao:
  - inexistencia de consumidor real

### `GET /api/v1/chart_data`

- contrato novo alvo:
  - `GET /api/v1/market/chart-data`
- estrategia:
  - manter via alias temporario
- tipo de compatibilidade:
  - adaptador de caminho
- criterio de remocao:
  - frontend consumir nome canonico novo

### `GET /api/v1/market_analysis`

- contrato novo alvo:
  - `GET /api/v1/market/analysis`
- estrategia:
  - manter via alias temporario
- tipo de compatibilidade:
  - adaptador de caminho
- criterio de remocao:
  - consumidores migrarem para rota canonica

### `POST /api/model/train`

- contrato novo alvo:
  - `POST /api/v1/model/train`
- estrategia:
  - manter alias temporario
- tipo de compatibilidade:
  - alias de rota
- criterio de remocao:
  - clientes passarem a usar rota versionada

### `GET /api/simulation`

- contrato novo alvo:
  - `GET /api/v1/simulation/report`
- estrategia:
  - manter enquanto a UI depender do payload composto
- tipo de compatibilidade:
  - alias de rota
  - adaptador de payload
- criterio de remocao:
  - dashboard reconciliado com o report novo

### `POST /api/simulation/run`

- contrato novo alvo:
  - `POST /api/v1/simulation/run`
- estrategia:
  - manter alias temporario
- tipo de compatibilidade:
  - alias de rota
- criterio de remocao:
  - consumidores mudarem para a rota nova

### `GET /api/simulation/status`

- contrato novo alvo:
  - `GET /api/v1/simulation/status`
- estrategia:
  - manter alias temporario
- tipo de compatibilidade:
  - alias de rota
- criterio de remocao:
  - UI/BFF migrarem

### `GET /api/simulation/summary`

- contrato novo alvo:
  - `GET /api/v1/simulation/summary`
- estrategia:
  - manter alias temporario
- tipo de compatibilidade:
  - alias de rota
- criterio de remocao:
  - dashboard e consumers migrarem

### `GET /api/v1/summary`

- contrato novo alvo:
  - `GET /api/v1/simulation/summary`
- estrategia:
  - deprecar imediatamente
- tipo de compatibilidade:
  - adaptador de payload apenas durante transicao curta
- criterio de remocao:
  - nenhuma dependencia ativa do shape legado

Restricao:

- nao preservar side effect de executar simulacao em query.

### `GET /api/v1/trade_history`

- contrato novo alvo:
  - `GET /api/v1/simulation/trades`
- estrategia:
  - manter alias temporario
- tipo de compatibilidade:
  - alias de rota
  - adaptador de payload
- criterio de remocao:
  - consumidores migrarem para query pura nova

Restricao:

- nao preservar reexecucao implicita do sistema.

### `GET /api/v1/backtest_period`

- contrato novo alvo:
  - `GET /api/v1/simulation/period`
- estrategia:
  - manter alias temporario
- tipo de compatibilidade:
  - alias de rota
- criterio de remocao:
  - dashboard e relatórios migrarem

Restricao:

- nao preservar dependencia de cache ou execucao indireta.

### `GET /api/v1/positions`

- contrato novo alvo:
  - `GET /api/v1/simulation/positions`
- estrategia:
  - manter alias temporario
- tipo de compatibilidade:
  - alias de rota
- criterio de remocao:
  - consumers migrarem para o path canonico

## 5.2 WebSockets

### `WS /ws/logs`

- stream novo alvo:
  - `WS /api/v1/ws/system/logs`
- estrategia:
  - manter alias temporario
- criterio de remocao:
  - consumidores migrarem para stream versionado

### `WS /api/ws/pulse`

- stream novo alvo:
  - `WS /api/v1/ws/system/pulse`
- estrategia:
  - manter alias temporario com contrato de metadata claro
- criterio de remocao:
  - pulse page usar stream novo

### `WS /api/ws/ticker`

- stream novo alvo:
  - `WS /api/v1/ws/market/ticker`
- estrategia:
  - manter apenas se houver decisao clara sobre `mock`, `derived`, `real` ou `disabled`
- criterio de remocao:
  - UI migrar para stream novo ou ticker antigo ser explicitamente aposentado

Restricao:

- nao manter ticker legado com aparencia de dado real se ele continuar sintetico.

## 6. Regras de Deprecacao

Toda rota ou stream legado deve ter:

- nome canonico substituto;
- data ou fase-alvo de remocao;
- consumidor conhecido;
- criterio objetivo de remocao;
- dono responsavel pela retirada.

Direcao recomendada:

- marcar como `deprecated` no contrato e na documentacao assim que o substituto existir;
- nao esperar o corte final para documentar deprecacao.

## 7. Janela de Convivencia Recomendada

Regra operacional recomendada:

- compatibilidade curta para aliases simples;
- compatibilidade media para payloads consumidos pelo frontend atual;
- compatibilidade minima ou nenhuma para contratos que hoje carregam side effect errado.

Ordem pratica:

1. criar contrato novo;
2. apontar alias legado para implementacao nova;
3. migrar consumidor;
4. marcar legado como deprecated;
5. remover legado.

## 8. O que Nao Deve Ser Preservado

Mesmo com compatibilidade, estes comportamentos nao devem continuar:

- `GET` disparando simulacao, treino ou execucao pesada;
- fallback silencioso que faz dado parecer real;
- ticker mockado parecendo feed operacional;
- shape diretamente acoplado a tabela fisica;
- logica paralela em endpoint legado e endpoint novo.

## 9. Sinais para Liberar Remocao do Legado

Podemos remover compatibilidade quando:

- consumidor conhecido ja estiver migrado;
- observabilidade mostrar ausencia de uso do alias legado;
- payload novo estiver aceito pela UI;
- nao houver regressao funcional na baseline da fase;
- documentacao estiver atualizada.

## 10. Checklist Operacional de Compatibilidade

- [ ] Mapear consumidor por endpoint legado.
- [ ] Definir substituto canonico de cada rota e stream.
- [ ] Definir tipo de compatibilidade de cada item.
- [ ] Definir criterio de remocao de cada item.
- [ ] Marcar quais comportamentos nao podem ser preservados.
- [ ] Definir owners da remocao por grupo de contrato.
- [ ] Atualizar docs quando o substituto existir.

## 11. Status do Entregavel

- status: `draft-initial`
- pronto para guiar a convivencia entre legado e nova API/WebSocket
- deve ser refinado quando a reconciliacao do frontend ficar mais detalhada na Fase 6
