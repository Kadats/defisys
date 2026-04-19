# Fase 0: Baseline de Testes e Regressao

## 1. Objetivo

Avaliar a suite atual de testes para responder:

- o que realmente protege comportamento;
- o que apenas mocka implementacao;
- o que e fragil ou perigoso para a reescrita;
- qual o conjunto minimo de regressao que precisamos preservar para entrar na Fase 1 com seguranca.

## 2. Leitura Executiva

A suite atual tem boa cobertura nominal de areas importantes:

- risco;
- estrategias;
- ML;
- API;
- LLM;
- engine;
- matematica financeira.

Mas ela nao e uniformemente confiavel.

Principais conclusoes:

- ha um nucleo bom de testes de dominio e matematica que vale preservar;
- testes de API cobrem contratos basicos, mas em geral com alto mocking;
- alguns testes da engine e estrategias ainda dependem de contornos artificiais ou arranjos manuais;
- o `conftest.py` torna a suite estruturalmente fragil ao tentar copiar dados do banco principal;
- para a reescrita, precisamos separar a suite em camadas e criar uma baseline minima mais rigorosa.

Observacao operacional importante:

- nesta sessao nao foi possivel executar a suite localmente porque o ambiente atual nao tem `poetry` instalado;
- tambem nao foi possivel validar o frontend com lint porque as dependencias nao estavam instaladas.

Ou seja:

- a analise abaixo e estrutural, baseada no codigo dos testes;
- a validacao executavel ainda precisa ser retomada em ambiente pronto.

## 3. Inventario da Suite Atual

Arquivos identificados em `tests/`:

- `conftest.py`
- `red_team_api_check.py`
- `test_accumulator_strategy.py`
- `test_api.py`
- `test_btc_lite_strategy.py`
- `test_control_center_api.py`
- `test_decimal_integration.py`
- `test_dynamic_risk.py`
- `test_ensemble.py`
- `test_heuristics.py`
- `test_kill_switch.py`
- `test_llm_agent.py`
- `test_math_financial.py`
- `test_math_lending.py`
- `test_math_uniswap.py`
- `test_policy_layer.py`
- `test_prediction.py`
- `test_pure_spot.py`
- `test_regime_classifier.py`
- `test_risk_manager.py`
- `test_rpc_manager.py`
- `test_sentiment.py`
- `test_setup_logging_and_config.py`
- `test_short_strategy.py`
- `test_sizing.py`
- `test_sma200_feature.py`
- `test_smart_dca.py`
- `test_smart_harvest.py`
- `test_strategy_factory.py`
- `test_stress_execution.py`
- `test_trading_engine.py`

## 4. Classificacao por Camada

## 4.1 Testes de Dominio / Matematica Pura

Valor para a reescrita: `alto`

Arquivos principais:

- `test_math_financial.py`
- `test_math_lending.py`
- `test_math_uniswap.py`
- `test_risk_manager.py`
- `test_dynamic_risk.py`
- `test_regime_classifier.py`
- `test_ensemble.py`
- `test_prediction.py`
- `test_sma200_feature.py`
- partes de `test_sizing.py`

Por que sao valiosos:

- testam regras que devem sobreviver a qualquer reorganizacao de arquitetura;
- em geral trabalham com entradas e saidas pequenas e objetivas;
- sao bons candidatos a virarem baseline de paridade da Fase 1 e Fase 2.

Riscos observados:

- alguns thresholds e mensagens podem estar muito acoplados ao comportamento atual, mas o valor central e alto;
- alguns testes de ML usam dados sinteticos simplificados demais, o que protege forma, nao necessariamente performance real.

## 4.2 Testes de Estrategia

Valor para a reescrita: `medio a alto`

Arquivos principais:

- `test_accumulator_strategy.py`
- `test_btc_lite_strategy.py`
- `test_pure_spot.py`
- `test_short_strategy.py`
- `test_smart_dca.py`
- `test_smart_harvest.py`
- `test_policy_layer.py`
- `test_strategy_factory.py`

Por que sao valiosos:

- capturam o comportamento esperado de entrada, saida, abstencao e defesa;
- protegem o uso de `prediction_proba`, health factor e roteamento por regime;
- sao essenciais para validar que a reescrita nao mudou a intencao das estrategias.

Fragilidades:

- muitos testes dependem de `MagicMock` ou engine parcialmente simulada;
- parte dos comportamentos e validada por chamadas esperadas, nao por resultado consolidado de portfolio;
- alguns comentarios indicam adaptacao manual para contornar dependencias de banco ou detalhes do engine.

Conclusao:

- devem ser preservados;
- na reescrita, vale converter parte deles para testes sobre contratos puros de decisao.

## 4.3 Testes da Engine

Valor para a reescrita: `medio`

Arquivos principais:

- `test_trading_engine.py`
- `test_kill_switch.py`
- `test_stress_execution.py`

Por que sao valiosos:

- cobrem pontos muito sensiveis:
  - abertura/fechamento de LP
  - fees
  - emergency shutdown
  - drawdown

Fragilidades:

- alguns cenarios dependem de patching de funcoes de banco;
- outros constroem estado manualmente em vez de passar pelos fluxos normais;
- protegem partes importantes, mas ainda muito ligadas a implementacao atual do engine.

Conclusao:

- nao devem ser descartados;
- devem ser complementados por testes de portfolio/risk mais puros na nova arquitetura.

## 4.4 Testes de API

Valor para a reescrita: `medio`

Arquivos principais:

- `test_api.py`
- `test_control_center_api.py`

Por que sao valiosos:

- protegem contratos basicos dos endpoints;
- ajudam a detectar regressao superficial durante modularizacao da API.

Fragilidades:

- alto uso de patching;
- verificam principalmente estrutura de resposta e status code;
- em varios casos nao exercitam o fluxo real por tras da rota.

Conclusao:

- sao bons como smoke tests de interface;
- nao sao suficientes como prova de corretude do backend.

## 4.5 Testes do LLM e Integracoes Externas

Valor para a reescrita: `alto`

Arquivos principais:

- `test_llm_agent.py`
- `test_rpc_manager.py`
- `test_sentiment.py`
- `red_team_api_check.py`

Por que sao valiosos:

- protegem o envelope do LLM, que e parte importante do produto;
- validam parsing, fallback e decisao heuristica;
- protegem regras de seguranca como proibicao de saque em producao;
- ajudam a garantir que resiliencia e seguranca nao se percam na reescrita.

Fragilidades:

- ainda sao fortemente mockados;
- validam mais o envelope do que o ganho quantitativo do LLM;
- nao existem, pelo menos na suite observada, benchmarks formais comparando LLM versus baseline heuristica em dataset congelado.

Conclusao:

- sao obrigatorios para a reescrita;
- precisam ser complementados por testes de avaliacao offline do comportamento do LLM.

## 5. Fragilidades Estruturais da Suite

## 5.1 `conftest.py` e o maior problema atual

Problema:

- a fixture de sessao tenta copiar os ultimos candles da base principal para a base de teste;
- isso cria dependencia acidental do ambiente e do estado do banco principal.

Impacto:

- baixa reprodutibilidade;
- risco operacional;
- suite pode passar ou falhar conforme o ambiente, nao conforme o codigo.

Classificacao:

- `critico`

## 5.2 Excesso de patching em rotas e servicos

Problema:

- muitos testes de API e integracao validam apenas que mocks foram chamados ou que o payload tem certo formato.

Impacto:

- dificil saber se o sistema ponta a ponta continua coerente;
- facil ter “suite verde” com comportamento real quebrado.

## 5.3 Mistura de testes de dominio com contornos de infraestrutura

Problema:

- alguns testes do engine e de estrategia precisam contornar banco ou montar estado artificialmente.

Impacto:

- indica que o dominio ainda nao esta isolado;
- aumenta custo de manutencao dos testes.

## 5.4 Ausencia de dataset golden formal para regressao

Problema:

- existe bastante teste unitario, mas nao aparece um dataset oficial pequeno e deterministico para comparar:
  - sinais
  - decisoes
  - resultados de simulacao

Impacto:

- dificulta medir paridade da reescrita.

## 6. O Que a Suite Atual Protege Bem

Protege relativamente bem:

- formula de health factor;
- limites de drawdown e kill switch;
- thresholds de varias estrategias;
- parsing e fallback do LLM;
- estrutura basica dos endpoints do control center;
- calculos financeiros utilitarios;
- presenca de `prediction_proba` no pipeline de ML.

## 7. O Que a Suite Atual Protege Mal

Protege mal ou de forma insuficiente:

- fluxo ponta a ponta real:
  - sync -> feature -> treino -> predicao -> simulacao -> summary
- diferenca entre simulacao historica e paper trading;
- consistencia do banco sem depender do ambiente;
- payloads reais do frontend apos fallback/proxy;
- impacto quantitativo do uso do LLM contra baseline heuristica;
- separacao entre leitura e comandos na API.

## 8. Baseline Minima de Regressao Recomendada

Para entrar na Fase 1 e Fase 2 com seguranca, a reescrita precisa preservar pelo menos este conjunto minimo:

### Bloco A. Dominio de risco

- health factor
- safe balance
- drawdown limits
- kill switch
- emergency close / defense logic

### Bloco B. Dominio quantitativo

- no look-ahead
- target generation
- `prediction_proba` entre 0 e 1
- thresholds de regime
- ensemble veto

### Bloco C. Estrategias centrais

- `AccumulatorStrategy`
- `BTCLiteStrategy`
- `PolicyLayerStrategy`
- `ShortStrategy`

### Bloco D. Envelope do LLM

- parsing de JSON
- decisao fallback
- normalizacao da acao
- decisao com falha do provedor

### Bloco E. Contratos publicos minimos

- `POST /api/model/train`
- `POST /api/simulation/run`
- `GET /api/simulation/status`
- `GET /api/system/health`
- `GET /api/system/indicators`
- `WS /api/ws/pulse`
- `WS /api/ws/ticker`

## 9. Suite Recomendada para a Nova Arquitetura

Na reescrita, a suite deve ser reorganizada em quatro niveis:

## Nivel 1. Unitarios Puros

- dominio de risco
- portfolio
- sizing
- regime
- LLM decision normalization
- rules de strategy decision

## Nivel 2. Integracao de Persistencia

- repositories
- mapeamento de tabelas
- summaries
- posicoes
- predicoes

Com banco dedicado e fixture sintetica.

## Nivel 3. Integracao de Casos de Uso

- `train_model`
- `generate_predictions`
- `run_backtest`
- `summarize_backtest`
- `get_control_center_snapshot`

## Nivel 4. Smoke de API

- contratos HTTP
- WebSockets
- BFF/proxies essenciais

## 10. Cenarios Golden Recomendados

Criar dataset pequeno e deterministico cobrindo:

- regime bull com drawdown controlado;
- regime bear com sinal forte de queda;
- regime uncertain com abstencao;
- posicao alavancada com defesa por HF;
- acionamento de kill switch;
- LLM indisponivel com fallback heuristico;
- LLM respondendo decisao valida normalizada.

Esses cenarios devem permitir comparar:

- decisao antiga;
- decisao nova;
- summary final;
- eventos essenciais da simulacao.

## 11. Decisoes Recomendadas para Fase 7

1. Reescrever `conftest.py` para eliminar dependencia do banco principal.
2. Criar fixtures sinteticas versionadas.
3. Criar um dataset golden oficial.
4. Reduzir o patching nos testes de API e mover parte da confianca para testes de caso de uso.
5. Criar avaliacao offline do LLM comparando:
   - decisao do modelo
   - fallback heuristico
   - resultado esperado em cenarios fixos

## 12. Conclusao

A suite atual nao e ruim. Ela ja tem varios sinais de maturidade e cobre areas realmente importantes.

O problema e estrutural:

- ela ainda mistura ambiente, implementacao e contrato;
- falta um baseline de regressao realmente hermetico;
- falta uma camada intermediaria de testes de caso de uso.

Resumo:

- existe material suficiente para proteger a reescrita;
- mas nao da para confiar cegamente na suite atual sem reforma;
- o primeiro alvo obrigatorio futuro e o `conftest.py`.

## 13. Status do Entregavel

- status: `draft-initial`
- pronto para servir como baseline de testes da Fase 0
