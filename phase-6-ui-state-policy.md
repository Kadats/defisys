# Fase 6: Politica de Estados de UI

## 1. Objetivo

Este documento define como a UI deve representar estados de dado e disponibilidade durante a reconciliacao da Fase 6.

## 2. Problema Atual

Hoje a interface mistura:

- dado real;
- dado derivado;
- fallback silencioso;
- mock tecnico;
- placeholder visual.

Isso cria uma UX bonita, mas semanticamente ambigua.

## 3. Estados Canonicos de UI

Toda area critica da UI deve conseguir representar, de forma explicita:

- `real`
- `derived`
- `mock`
- `degraded`
- `disabled`
- `loading`
- `empty`
- `error`

## 4. Definicao de Cada Estado

## 4.1 `real`

Definicao:

- dado vindo da fonte operacional esperada.

Uso:

- health real;
- logs reais;
- resumo de simulacao oficial;
- feed de mercado realmente conectado.

Sinalizacao recomendada:

- badge neutra ou positiva;
- sem copy enganosa de “simulado”.

## 4.2 `derived`

Definicao:

- dado calculado a partir de fontes confiaveis, mas nao feed bruto primario.

Uso:

- pulse agregado;
- indicadores calculados a partir de snapshots;
- metricas consolidadas.

Sinalizacao recomendada:

- badge discreta indicando “Derived” ou equivalente;
- tooltip ou detalhe curto quando necessario.

## 4.3 `mock`

Definicao:

- dado sintetico ou laboratorial.

Uso:

- ticker sintetico;
- sandbox fake;
- qualquer simulacao de UX.

Sinalizacao recomendada:

- badge visivel;
- copy explicita;
- nunca usar apenas cor verde e animacao de “live” sem contexto.

## 4.4 `degraded`

Definicao:

- sistema respondeu, mas em modo parcial, fallback ou contingencia.

Uso:

- indicadores offline com ultimo snapshot valido;
- health parcial;
- stream com perda de origem principal.

Sinalizacao recomendada:

- badge de alerta;
- descricao curta da degradacao;
- manter usabilidade sem fingir normalidade.

## 4.5 `disabled`

Definicao:

- funcionalidade intencionalmente desligada.

Uso:

- stream ainda nao liberado;
- modulo temporariamente desativado.

Sinalizacao recomendada:

- mensagem direta de indisponibilidade planejada;
- nao apresentar loading infinito.

## 4.6 `loading`

Definicao:

- requisicao ou stream ainda inicializando.

Regra:

- loading deve ter timeout visual claro;
- nao pode virar estado permanente silencioso.

## 4.7 `empty`

Definicao:

- nao ha dado disponivel, mas isso nao e erro.

Uso:

- historico vazio;
- simulacao ainda nao rodada;
- lista de trades vazia.

## 4.8 `error`

Definicao:

- falha real no carregamento ou processamento.

Regra:

- erro deve ser distinguivel de `degraded`;
- nao converter erro em dado aparentemente valido.

## 5. Aplicacao por Area

## 5.1 Ticker Header

Problema atual:

- usa preco default e simula ETH;
- o usuario ve um ticker funcional mesmo sem garantia de dado real.

Politica recomendada:

- mostrar badge `mock`, `derived` ou `real`;
- nao usar preco fallback como se fosse mercado vivo;
- quando nao houver feed, mostrar estado `disabled`, `degraded` ou `error`.

## 5.2 Indicator Widget

Problema atual:

- defaults locais escondem falha.

Politica recomendada:

- indicadores devem exibir `source_status`;
- se o dado for fallback, isso precisa aparecer como `degraded`;
- regime default nao deve parecer analise real.

## 5.3 Dashboard

Problema atual:

- mistura cards reais com console cenografico e bloco placeholder.

Politica recomendada:

- placeholders devem ser tratados como placeholders;
- areas ainda nao integradas devem dizer isso claramente;
- “LIVE FEED” so quando houver dado coerente com esse termo.

## 5.4 System Pulse

Problema atual:

- o stream parece funcional, mas nao explicita semantica operacional.

Politica recomendada:

- mostrar estado de conexao;
- mostrar estado de origem (`real`, `derived`, `degraded`);
- nao depender apenas do WS conectado/desconectado.

## 5.5 Sandbox

Problema atual:

- visual maduro para backend de laboratorio.

Politica recomendada:

- manter a linguagem de laboratorio;
- exibir badge `mock` ou `laboratory`;
- nao vender o sandbox como runtime produtivo.

## 5.6 Login

Problema atual:

- placeholder simples.

Politica recomendada:

- exibir como fluxo indisponivel/placeholder;
- nao passar impressao de autenticacao funcional se nao houver backend real.

## 6. Regras de Copy e Sinalizacao

- usar linguagem curta e objetiva;
- preferir badge ou label pequena a texto escondido em tooltip apenas;
- evitar “online”, “live”, “secure”, “ready” quando o estado real nao sustenta a copy;
- copy institucional so deve aparecer quando houver comportamento consistente por baixo.

## 7. Regras de Implementacao Futura

- `source_status` vindo do backend deve ser insumo primario da UI;
- fallback local no frontend nao deve inventar semanticamente um estado melhor do que o backend tem;
- quando a UI criar degradacao local, ela deve rotular isso explicitamente;
- nenhum componente principal deve ficar sem politica de estado.

## 8. Status do Entregavel

- status: `draft-initial`
- pronto para orientar a reconciliacao semantica da UI na Fase 6
- deve ser aplicado junto com os contratos da Fase 5 e o mapa do frontend
