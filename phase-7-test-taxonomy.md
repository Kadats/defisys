# Fase 7: Taxonomia da Suite de Testes

## 1. Objetivo

Este documento define a taxonomia-alvo da suite de testes.

## 2. Leitura Executiva

Conclusao principal:

- a suite atual tem valor real, mas esta organizada muito mais por historico de arquivo do que por responsabilidade arquitetural;
- a nova taxonomia precisa separar claramente dominio, aplicacao, infraestrutura e interfaces;
- hoje existe excesso de patching em API e estrategia, enquanto o maior risco estrutural esta no ambiente de teste e no `conftest.py`.

## 3. Categorias Oficiais da Nova Suite

## 3.1 Unitario de Dominio

Finalidade:

- validar regras puras de risco, portfolio, sizing, regime, matematica financeira e decisao.

Caracteristicas:

- sem banco;
- sem FastAPI;
- sem arquivo real;
- sem rede;
- sem patching estrutural desnecessario.

Candidatos naturais da suite atual:

- `test_math_financial.py`
- `test_math_lending.py`
- `test_math_uniswap.py`
- `test_risk_manager.py`
- `test_dynamic_risk.py`
- `test_regime_classifier.py`
- `test_heuristics.py`
- partes de `test_sizing.py`

## 3.2 Unitario de Estrategia

Finalidade:

- validar decisao de estrategia sobre contratos pequenos e controlados.

Caracteristicas:

- pode usar fakes leves de engine ou portfolio;
- nao deve depender de banco;
- deve migrar do mock de chamada para resultado de decisao sempre que possivel.

Candidatos naturais:

- `test_accumulator_strategy.py`
- `test_btc_lite_strategy.py`
- `test_pure_spot.py`
- `test_short_strategy.py`
- `test_smart_dca.py`
- `test_smart_harvest.py`
- `test_policy_layer.py`
- `test_strategy_factory.py`

## 3.3 Unitario de Aplicacao

Finalidade:

- validar commands e queries da camada `application`.

Caracteristicas:

- usa portas abstratas mockadas ou fakes;
- valida orquestracao, DTOs, warnings e fluxo;
- nao conhece FastAPI nem banco real.

Estado atual:

- categoria ainda pouco representada;
- sera importante quando as Fases 2 e 3 forem executadas.

## 3.4 Integracao de Repository

Finalidade:

- validar leitura e escrita em banco de forma real e isolada.

Caracteristicas:

- usa banco de teste dedicado;
- sem copiar dados da base principal;
- valida schema, transacao, mapeamento e consulta real.

Estado atual:

- quase ausente como categoria explicita;
- hoje varios testes contornam isso com patching ou estado manual.

## 3.5 Integracao de Gateway

Finalidade:

- validar adaptadores de infraestrutura externa sem depender do provider real em producao.

Caracteristicas:

- pode usar responses controladas;
- valida parsing, timeout, retry, erro tipado e fallback;
- idealmente separa fake de mock bruto.

Candidatos naturais:

- `test_rpc_manager.py`
- `test_sentiment.py`
- `test_llm_agent.py`
- `red_team_api_check.py`

## 3.6 Smoke de API

Finalidade:

- validar contratos HTTP criticos e wiring minimo da interface web do backend.

Caracteristicas:

- usa TestClient;
- patching minimo e consciente;
- valida status, shape e comportamento proibido, como `GET` com side effect.

Candidatos naturais:

- `test_api.py`
- `test_control_center_api.py`

## 3.7 Smoke de Frontend / BFF

Finalidade:

- validar que o frontend/BFF consome contratos esperados sem regressao grosseira.

Caracteristicas:

- foco em rotas BFF, fallback, estados de erro e wiring critico;
- nao substituir testes completos de UI.

Estado atual:

- praticamente inexistente como categoria formal;
- precisa nascer na nova estrategia.

## 3.8 Testes Especiais do Envelope do LLM

Finalidade:

- validar contrato, fallback, seguranca, parsing, acoes permitidas e restricoes operacionais.

Caracteristicas:

- nao medem alpha quantitativo;
- medem seguranca e consistencia do edge de IA.

Categoria obrigatoria:

- a IA permanece componente central do sistema e precisa de trilha propria de validacao.

## 4. Mapeamento da Suite Atual para a Taxonomia

## 4.1 Preservar com prioridade alta

- `test_math_financial.py`
- `test_math_lending.py`
- `test_math_uniswap.py`
- `test_risk_manager.py`
- `test_dynamic_risk.py`
- `test_prediction.py`
- `test_regime_classifier.py`
- `test_llm_agent.py`
- `test_rpc_manager.py`
- `test_sentiment.py`
- `test_kill_switch.py`

## 4.2 Preservar, mas refatorar de categoria

- `test_accumulator_strategy.py`
- `test_btc_lite_strategy.py`
- `test_pure_spot.py`
- `test_short_strategy.py`
- `test_smart_dca.py`
- `test_smart_harvest.py`
- `test_policy_layer.py`
- `test_strategy_factory.py`
- `test_trading_engine.py`
- `test_stress_execution.py`

Motivo:

- sao valiosos, mas hoje ainda muito proximos do engine atual ou de mocks de chamada.

## 4.3 Manter como smoke temporario

- `test_api.py`
- `test_control_center_api.py`

Motivo:

- protegem contrato superficial durante a migracao;
- precisam ser substituidos ou complementados por smoke mais aderente a contratos novos.

## 4.4 Reavaliar e reclassificar

- `test_decimal_integration.py`
- `test_setup_logging_and_config.py`
- `red_team_api_check.py`

Motivo:

- verificar se entram como smoke de infraestrutura, seguranca ou testes especiais separados.

## 5. Regras de Nome e Localizacao Futuras

Direcao recomendada:

- `tests/unit/domain/`
- `tests/unit/application/`
- `tests/integration/db/`
- `tests/integration/gateways/`
- `tests/smoke/api/`
- `tests/smoke/frontend/`
- `tests/special/llm/`

Regra:

- nome do arquivo deve refletir o contrato ou o fluxo testado, nao o acidente historico do modulo.

## 6. O que Nao Queremos Repetir

- teste de API que so valida se mock foi chamado;
- teste de estrategia que so valida chamada de metodo do engine, sem semantica;
- fixture global que depende da base principal;
- smoke que passa porque o fallback inventou dado plausivel;
- mistura de unitario puro com side effect de infraestrutura.

## 7. Status do Entregavel

- status: `draft-initial`
- pronto para orientar a reorganizacao da suite na Fase 7
- deve ser refinado quando a execucao da fase comecar
