# Fase 5: Plano de WebSockets

## 1. Objetivo

Este documento define o plano de WebSockets da Fase 5.

A meta aqui e deixar explicito:

- quais streams existem;
- para que cada stream serve;
- qual o contrato de payload;
- qual o estado operacional de cada stream;
- como a migracao deve tratar streams reais, mockados ou degradados.

## 2. Principios dos WebSockets

- WebSocket e interface formal, nao atalho improvisado;
- cada stream precisa ter contrato claro de evento;
- todo stream precisa declarar origem e status do dado;
- stream mockado nao pode parecer stream produtivo;
- stream de log nao substitui endpoint HTTP quando consulta paginada fizer mais sentido;
- o frontend deve conseguir distinguir desconexao, degradacao e mock.

## 3. Classificacao Operacional Padrao

Todo stream da nova arquitetura deve carregar classificacao operacional explicita:

- `real`
  - dados vindos de fonte operacional ou runtime real
- `derived`
  - dados derivados de estado consolidado, sem ser feed tick-by-tick nativo
- `mock`
  - stream sintetico usado para laboratorio, UX ou demonstracao
- `degraded`
  - stream operando com fallback parcial
- `disabled`
  - stream intencionalmente desligado

Direcao recomendada:

- expor esse status no handshake inicial;
- repetir esse status em eventos de metadata quando houver mudanca relevante;
- nunca depender so do nome da rota para inferir o tipo do stream.

## 4. Estrutura de Eventos Recomendada

Cada conexao deve ter, no minimo, dois tipos conceituais de evento:

- evento de `meta`
- evento de `data`

Shape conceitual recomendado:

```text
{
  type,
  stream,
  emitted_at,
  source_status,
  payload
}
```

Campos recomendados:

- `type`
  - `meta`
  - `snapshot`
  - `update`
  - `warning`
  - `error`
- `stream`
  - nome canonico do stream
- `emitted_at`
  - timestamp do evento
- `source_status`
  - `real`, `derived`, `mock`, `degraded`, `disabled`
- `payload`
  - conteudo tipado do evento

## 5. Streams Atuais e Destino Planejado

## 5.1 `WS /ws/logs`

Finalidade atual:

- stream generico de logs

Leitura atual:

- aparentemente real;
- simples;
- usado como base do pulse.

Destino planejado:

- stream canonico de logs em camada propria de websocket;
- nome canonico sugerido:
  - `WS /api/v1/ws/system/logs`

Status operacional esperado:

- `real`

Eventos recomendados:

- `meta`
- `update`

Payload de `update`:

- `timestamp`
- `level`
- `message`
- `source`

Observacoes:

- manter `GET /api/v1/system/logs` como caminho de consulta paginada;
- o websocket fica para stream incremental, nao para historico completo.

## 5.2 `WS /api/ws/pulse`

Finalidade atual:

- alias do stream de logs para o frontend System Pulse

Leitura atual:

- funcionalmente real;
- dependente da UI atual.

Destino planejado:

- convergir para stream especifico de pulse ou alias temporario do stream de logs;
- nome canonico sugerido:
  - `WS /api/v1/ws/system/pulse`

Status operacional esperado:

- `derived`

Eventos recomendados:

- `meta`
- `snapshot`
- `update`

Payload sugerido:

- `entries`
- `health_summary`
- `warnings`

Observacoes:

- pulse nao deve ser apenas alias opaco de log se o frontend espera semantica operacional;
- se continuar como alias temporario, isso deve ser declarado no contrato.

## 5.3 `WS /api/ws/ticker`

Finalidade atual:

- stream de ticker para o War Room

Leitura atual:

- mockado com geracao sintetica;
- vendido visualmente como “live”.

Destino planejado:

Ha tres caminhos aceitos, e a fase precisa escolher um:

1. manter stream, mas com `source_status = mock` visivel;
2. substituir por feed real ou derivado confiavel;
3. desativar o stream ate existir fonte operacional valida.

Nome canonico sugerido:

- `WS /api/v1/ws/market/ticker`

Status operacional permitido na transicao:

- `mock`
- `derived`
- `real`
- `disabled`

Eventos recomendados:

- `meta`
- `snapshot`
- `update`
- `warning`

Payload sugerido:

- `symbol`
- `price`
- `change_24h_pct`
- `volume_24h`
- `source_label`

Observacoes:

- se o stream continuar sintetico, o payload deve afirmar isso;
- nao usar nome, cor ou copy que sugira feed de producao quando o dado nao for real.

## 6. Handshake Inicial Recomendado

Cada conexao nova deve receber um evento `meta` inicial contendo:

- `stream`
- `source_status`
- `schema_version`
- `connected_at`
- `heartbeat_interval_ms`
- `warning` opcional

Motivo:

- facilitar debug;
- reduzir ambiguidade de estado no frontend;
- permitir UX diferente para stream real, mockado ou degradado.

## 7. Heartbeat, Reconexao e Falhas

Definir para todos os streams:

- intervalo de heartbeat;
- timeout de inatividade;
- politica de reconexao do cliente;
- diferenca entre stream desconectado e stream desativado;
- mensagem padrao de erro.

Direcao recomendada:

- heartbeat leve e previsivel;
- erro explicito quando a origem ficar indisponivel;
- evento `warning` antes de cair para degradacao quando possivel.

## 8. Compatibilidade com a UI Atual

Consumidores mapeados:

- dashboard principal usa ticker
- `TickerHeader` usa ticker
- pulse page usa pulse

Regras de compatibilidade:

- o frontend atual nao pode perder a capacidade de detectar conexao;
- mudanca de payload precisa vir com camada de compatibilidade temporaria;
- se `ticker` for mantido como mock, isso precisa ficar visivel no evento e, idealmente, na UI.

## 9. Ordem Recomendada de Migracao

Prioridade P0:

- formalizar `logs`
- formalizar `pulse`
- introduzir handshake `meta`

Prioridade P1:

- decidir destino do `ticker`
- classificar oficialmente `ticker` como `mock`, `derived`, `real` ou `disabled`
- alinhar consumidores do frontend

Prioridade P2:

- adicionar streams novos so depois de fechar os contratos centrais

## 10. Decisoes que a Fase Precisa Fechar

1. `pulse` vai ser stream proprio ou alias declarado de logs?
2. `ticker` continua existindo durante a transicao?
3. Se continuar, ele sera assumidamente `mock` ou ja vira `derived`/`real`?
4. Quais metadados minimos todo stream deve enviar no handshake?
5. Como a UI vai distinguir stream degradado de stream indisponivel?

## 11. Dependencias para o Proximo Artefato

Este plano deve alimentar:

- `phase-5-compatibility-plan.md`

## 12. Status do Entregavel

- status: `draft-initial`
- pronto para orientar o desenho dos contratos de websocket da Fase 5
- ainda depende da decisao final sobre o destino do ticker mockado
