# Fase 1: Contrato do LLM

## 1. Objetivo

Formalizar como o LLM entra no sistema sem contaminar o dominio e sem perder o edge que ele ja entrega hoje.

## 2. Leitura Executiva

O LLM permanece no caminho de decisao, mas deixa de ser um atalho informal espalhado entre prompt, parser e estrategia.

Diretriz principal:

- o LLM e uma porta externa de recomendacao;
- a resposta dele precisa ser normalizada;
- a decisao final continua sob controle do sistema;
- fallback heuristico continua obrigatorio;
- tudo precisa ser auditavel e comparavel offline.

## 3. Posicionamento Arquitetural

O LLM entra assim:

- `interfaces`: nao fala com o modelo diretamente
- `application`: coordena a consulta quando o caso de uso exigir
- `infrastructure`: implementa o cliente Gemini ou outro provider
- `domain`: recebe apenas uma decisao normalizada e validada

Regra:

- resposta bruta do provider nao atravessa a fronteira do dominio.

## 4. Contratos Canonicos

## 4.1 `RiskDecisionContext`

Tipo:

- DTO de entrada para a porta do LLM

Campos minimos:

- `timestamp`
- `usd_balance`
- `btc_collateral`
- `aave_debt_usd`
- `health_factor`
- `ml_confidence`
- `market_regime`
- `rsi`

Campos recomendados:

- `gas_reserve_usd`
- `global_drawdown_pct`
- `daily_drawdown_pct`
- `btc_price`
- `active_positions_count`
- `wallet_lp_value_usd`
- `aave_collateral_usd`
- `portfolio_equity_usd`
- `strategy_name`
- `environment`

Invariantes:

- `ml_confidence` entre `0.0` e `1.0`
- `rsi` entre `0` e `100`
- `health_factor` > `0`
- o contexto precisa refletir o instante da decisao
- o contexto nao pode carregar dados futuros

## 4.2 `LLMDecisionResponse`

Tipo:

- DTO normalizado de saida da porta do LLM

Campos minimos:

- `action`
- `amount_pct`
- `reason`

Campos recomendados:

- `provider`
- `model`
- `source`
- `latency_ms`
- `raw_response_ref`
- `validation_errors`

Invariantes:

- `action` precisa pertencer ao conjunto permitido
- `amount_pct` entre `0.0` e `1.0`
- `reason` string obrigatoria e curta

## 5. Conjunto Finito de Acoes Aceitas

Conjunto inicial recomendado:

- `DEFENSE_MODE`
- `BORROW_AND_LP`
- `CONSERVATIVE_LP`
- `SPOT_ONLY`
- `DO_NOTHING`

Regras:

- somente essas acoes podem sair da porta do LLM nesta fase;
- outras acoes de estrategia continuam internas ao dominio;
- provider que responder fora disso e considerado invalido.

## 6. Pipeline de Validacao

## 6.1 Passo 1. Chamada ao provider

Saida:

- texto bruto do provider

## 6.2 Passo 2. Extracao de estrutura

Saida:

- objeto JSON parseado, quando possivel

Falha:

- se nao houver JSON valido, fallback

## 6.3 Passo 3. Validacao semantica

Validar:

- acao permitida
- `amount_pct` em faixa valida
- `reason` presente

Falha:

- qualquer invalidez leva a fallback

## 6.4 Passo 4. Normalizacao

Saida:

- `LLMDecisionResponse` com:
  - provider
  - model
  - source=`llm`
  - campos clamped/normalizados se aplicavel

## 6.5 Passo 5. Conversao para decisao de dominio

Saida:

- `LLMDecision` ou `StrategyDecision` validada pelo sistema

Regra:

- guardrails de risco e kill switch ainda podem vetar ou substituir a recomendacao.

## 7. Contrato do Fallback Heuristico

O fallback precisa obedecer exatamente a mesma interface de saida:

- `action`
- `amount_pct`
- `reason`
- `source`

Regras:

- fallback e parte permanente do sistema, nao modo degradado improvisado;
- fallback deve ser deterministico;
- fallback deve ser auditavel;
- fallback deve ser testado com cenarios fixos.

`source` recomendado:

- `fallback`

## 8. Campos Minimos para Auditoria e Avaliacao Offline

Toda consulta ao LLM deve produzir ou permitir produzir estes campos:

- `timestamp`
- `run_id` ou referencia de execucao
- `strategy_name`
- `symbol`
- `timeframe`
- `risk_context_hash` ou referencia equivalente
- `prediction_confidence`
- `market_regime`
- `health_factor`
- `action_returned`
- `amount_pct_returned`
- `source`
- `provider`
- `model`
- `was_fallback`
- `validation_status`
- `latency_ms`

Campos desejaveis:

- `prompt_version`
- `features_version`
- `post_decision_outcome_ref`

## 9. Politicas por Ambiente

## 9.1 Test

- provider externo pode ser mockado;
- fallback deve ser exercitado obrigatoriamente;
- contrato deve ser validado por testes puros.

## 9.2 Backtest

- permitido usar LLM real ou modo replay, desde que auditavel;
- resultados devem distinguir claramente `llm` de `fallback`.

## 9.3 Paper Trading

- permitido, mas com telemetria reforcada;
- qualquer degradacao para fallback deve ficar visivel.

## 9.4 Producao futura

- requer limites de taxa, timeout, retry e politica de fail-safe;
- resposta invalida nunca pode gerar acao nao reconhecida.

## 10. Regras de Seguranca e Operacao

- timeout obrigatorio na chamada ao provider
- retry controlado apenas para erros transitórios
- parser robusto para JSON envelopado em markdown/html
- nenhuma resposta livre do modelo deve ser executada sem validacao
- kill switch e limites de risco sempre prevalecem sobre a recomendacao do LLM

## 11. Mapeamento com o Legado

- `consult_risk_agent(context)` -> porta de aplicacao/infrastructure
- `_consult_gemini(...)` -> provider adapter
- `_extract_json_from_text(...)` -> parser de infrastructure
- `_fallback_decision(...)` -> adapter heuristico compativel com a mesma interface
- resposta final atual da estrategia -> deve convergir para `StrategyDecision`

## 12. Casos de Teste Obrigatorios

- JSON puro valido
- JSON encapsulado em markdown
- JSON encapsulado em HTML
- resposta invalida
- acao fora do conjunto permitido
- `amount_pct` fora da faixa
- fallback para HF critico
- fallback para oversold
- fallback para alta confianca
- distincao clara entre `source=llm` e `source=fallback`

## 13. Conclusao

O contrato do LLM na arquitetura nova fica assim:

- entra `RiskDecisionContext`
- sai `LLMDecisionResponse`
- o sistema valida, normaliza e converte
- o dominio recebe apenas decisao segura e rastreavel

Com isso, preservamos o valor da IA sem deixar o nucleo dependente da forma instavel do provider.

