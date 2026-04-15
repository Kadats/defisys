# Fase 0: Invariantes do Sistema

## 1. Objetivo

Registrar as invariantes que a reescrita parcial nao pode destruir sem decisao explicita.

Este documento nao descreve “como o codigo atual faz”, e sim “o que precisa continuar verdadeiro” para que a reescrita preserve a intencao do produto.

## 2. Leitura Executiva

As invariantes centrais do DefiSys se agrupam em cinco blocos:

- integridade quantitativa;
- protecoes financeiras e de risco;
- isolamento operacional por ambiente;
- forma de uso do LLM;
- separacao conceitual entre simulacao, paper trading e eventual execucao real.

A reescrita pode mudar a forma da implementacao, mas nao pode quebrar estes compromissos sem uma decisao arquitetural explicita e documentada.

## 3. Invariantes Quantitativas

## 3.1 Zero Look-Ahead Bias

Status: `nao negociavel`

Invariante:

- features usadas por ML e decisao so podem usar informacao disponivel no momento da decisao;
- indicadores e colunas derivadas precisam respeitar o principio de usar candle fechado;
- `shift(1)` ou mecanismo equivalente deve continuar existindo para as features causais.

Base observada:

- documentado em `docs/AUDITORIA_INSTITUCIONAL.md`;
- implementado em `backend/src/data/pipeline.py`.

Implicacao para reescrita:

- qualquer pipeline novo precisa provar causalidade temporal;
- melhoria de performance ou legibilidade nao justifica remover esse guardrail.

## 3.2 Separacao entre feature, target e predicao

Status: `nao negociavel`

Invariante:

- dado bruto, feature engineering, target e predicao sao conceitos distintos;
- o target nao pode contaminar a feature;
- a predicao persistida deve continuar rastreavel e comparavel com o realizado.

Implicacao:

- reescrita deve manter contratos distintos para:
  - `MarketCandle`
  - `FeatureVector`
  - `Prediction`
  - `BacktestDecisionContext`

## 3.3 Threshold de confianca do ML

Status: `evolutivo com intencao preservada`

Invariante:

- o sistema usa `prediction_proba` como sinal central de confianca;
- thresholds podem mudar, mas a ideia de “decisao modulada por confianca” precisa permanecer.

Base observada:

- `ML_CONFIDENCE_THRESHOLD` em `config.py`;
- varias estrategias dependem diretamente de `prediction_proba`.

## 3.4 Regime e ensemble como camada de veto/roteamento

Status: `nao negociavel em intencao`

Invariante:

- a decisao final nao e apenas “predicao subiu ou caiu”;
- regime de mercado e filtros de confianca/volatilidade podem vetar ou redirecionar trades;
- regime `UNCERTAIN` deve continuar representando abstencao ou postura defensiva.

Base observada:

- `regime_classifier.py`
- `policy_layer.py`
- `ensemble.py`

## 4. Invariantes Financeiras e de Risco

## 4.1 Reserva de gas / solvencia operacional

Status: `nao negociavel`

Invariante:

- o sistema deve manter reserva minima em USD para custos operacionais;
- nao pode alocar 100% do saldo de forma a inviabilizar fechamento de posicoes;
- estrategia e engine devem considerar `GAS_RESERVE_USD`.

Base observada:

- `GAS_RESERVE_USD` em `config.py`;
- uso espalhado nas estrategias e no `RiskManager`.

## 4.2 Health Factor como limitador central de alavancagem

Status: `nao negociavel`

Invariante:

- novas alavancagens e refinanciamentos devem respeitar health factor;
- estados de warning, critical e liquidation precisam continuar existindo;
- se a posicao fica insegura, o sistema deve reduzir risco antes de continuar expondo capital.

Base observada:

- `RiskManager.calculate_health_factor`
- thresholds `HF_WARNING`, `HF_CRITICAL`, `HF_REFINANCE`
- estrategias `Accumulator` e `BTCLite`

## 4.3 Kill Switch por drawdown

Status: `nao negociavel`

Invariante:

- o sistema deve ter uma trava superior ao nivel de estrategia;
- se drawdown global ou diario exceder limites, novas ordens devem ser bloqueadas;
- o kill switch deve ter precedencia sobre sinais de IA, heuristica ou estrategia.

Base observada:

- `MAX_GLOBAL_DRAWDOWN`
- `MAX_DAILY_DRAWDOWN`
- `RiskManager.check_drawdown_limits`
- documentado em `docs/AUDITORIA_INSTITUCIONAL.md`

## 4.4 Deleverage e defesa antes de liquidation

Status: `nao negociavel em intencao`

Invariante:

- a plataforma deve tentar defender a carteira antes de liquidacao forçada;
- usar caixa/reserva para amortecer risco faz parte da tese do produto;
- fechar posicoes de forma defensiva e preferivel a seguir exposto de maneira cega.

## 4.5 Separacao conceitual das tesourarias

Status: `nao negociavel em intencao`

Invariante:

- o sistema distingue pelo menos estas visoes:
  - caixa/spot
  - alocacao em LP/DeFi
  - colateral/divida Aave
- o summary final deve continuar explicando a carteira nesses blocos.

Base observada:

- `simulation_summary`
- `/api/simulation/summary`

## 4.6 Nao executar ordens reais sem barreiras explicitas

Status: `nao negociavel`

Invariante:

- ambiente sandbox precisa continuar semanticamente seguro;
- execucao real nao pode acontecer por acidente em ambiente errado;
- qualquer caminho para producao precisa passar por validacoes extras.

## 5. Invariantes Operacionais e de Ambiente

## 5.1 Isolamento por ambiente

Status: `nao negociavel`

Invariante:

- `test`, `paper` e principal devem continuar separados;
- testes nao devem compartilhar banco com simulacao real nem historico principal;
- paper trading deve continuar sendo trilha distinta da simulacao historica.

## 5.2 Validacao de credenciais em producao

Status: `nao negociavel`

Invariante:

- em producao, segredos obrigatorios devem existir;
- em producao, chaves da exchange nao podem permitir saque;
- falha de validacao deve abortar comportamento sensivel.

Base observada:

- `validate_production_secrets`
- `BinanceExchangeClient.validate_api_permissions`

## 5.3 Resiliencia de provedores externos

Status: `nao negociavel em intencao`

Invariante:

- chamadas externas criticas precisam ter timeout, retry e fallback;
- no caso de RPC, o sistema precisa suportar failover entre provedores;
- o produto nao pode depender de um unico endpoint sem degradacao controlada.

Base observada:

- `RPCManager`
- docs de auditoria institucional

## 5.4 Startup nao pode comprometer previsibilidade

Status: `evolutivo`

Invariante:

- tarefas pesadas automatizadas devem ser controlaveis;
- o sistema nao deve ter startup “magico” sem rastreabilidade;
- sincronizacao automatica pode existir, mas deve ser observavel e configuravel.

## 6. Invariantes de Uso do LLM

## 6.1 O LLM faz parte do edge do sistema

Status: `nao remover`

Invariante:

- a IA nao e acessorio cosmético neste projeto;
- ela participa da tomada de decisao e, segundo a direcao do produto, contribui para os melhores resultados atuais;
- a reescrita nao deve remover esse papel.

## 6.2 O LLM nao pode operar sem envelope de controle

Status: `nao negociavel`

Invariante:

- a resposta do LLM precisa continuar validada estruturalmente;
- a decisao final deve caber em um conjunto finito de acoes conhecidas;
- o sistema precisa de fallback deterministico quando a chamada ao modelo falha ou retorna invalido;
- logs precisam deixar claro se a decisao veio do modelo ou do fallback.

Base observada:

- `backend/src/ai/llm_agent.py`
- docs de Gemini e arquitetura comparativa

## 6.3 O LLM deve consumir contexto de risco e carteira, nao so preco

Status: `nao negociavel em intencao`

Invariante:

- a decisao do LLM deve continuar considerando pelo menos:
  - health factor
  - saldo USD
  - colateral BTC
  - divida
  - confianca do ML
  - RSI ou sinais similares

## 6.4 O fallback heuristico continua existindo

Status: `nao negociavel`

Invariante:

- mesmo que o LLM seja relevante para performance, o sistema nao pode ficar sem resposta operacional quando ele falha;
- fallback heuristico e parte do envelope de confiabilidade.

## 6.5 O papel do LLM deve ser mensuravel

Status: `obrigatorio na reescrita`

Invariante desejado para a nova arquitetura:

- precisamos conseguir comparar:
  - decisao com LLM
  - decisao sem LLM
  - ganho real de precisao e resultado

Isto hoje existe parcialmente, mas precisa virar compromisso formal da nova base.

## 7. Invariantes de Simulacao e Paper Trading

## 7.1 Simulacao historica e paper trading nao sao a mesma coisa

Status: `nao negociavel`

Invariante:

- backtest historico e uma coisa;
- paper trading com feed real-time e outra;
- os fluxos podem compartilhar dominio, mas nao devem ser confundidos em runtime.

## 7.2 Summary oficial deve continuar existindo

Status: `nao negociavel em intencao`

Invariante:

- o sistema precisa continuar tendo uma “fonte oficial” de resumo do backtest/simulacao;
- a UI nao deve depender apenas de calculos efemeros em memoria.

Base observada:

- `simulation_summary`

## 7.3 Consultas nao devem disparar execucao sem decisao consciente

Status: `invariante alvo da reescrita`

Invariante desejado:

- uma query HTTP nao deve iniciar simulacao pesada implicitamente;
- leitura deve ser leitura; comando deve ser comando.

Observacao:

- hoje esta regra e violada em algumas rotas;
- isso deve ser corrigido, nao preservado.

## 8. O Que Pode Mudar Sem Violar as Invariantes

Pode mudar:

- estrutura de pastas;
- frameworks internos de persistencia;
- nome de services e repositories;
- thresholds finos de estrategia, se houver calibracao controlada;
- formato de payloads HTTP, desde que haja migracao compativel;
- detalhes de UI;
- forma de orquestracao entre treino, predicao e simulacao.

Nao pode mudar sem decisao explicita:

- no look-ahead;
- kill switch;
- reserva de gas;
- protecao por health factor;
- isolamento de ambiente;
- validacao de chave sem saque em producao;
- presenca do LLM como componente relevante;
- fallback deterministico para falha do LLM;
- separacao entre simulacao e paper trading.

## 9. Invariantes com Maior Peso na Fase 1

As invariantes mais importantes para abrir contratos de dominio sao:

1. `PortfolioState` deve representar caixa, BTC, colateral, divida e estado de risco.
2. `RiskSnapshot` deve representar health factor, drawdown, kill switch e solvencia.
3. `Prediction` deve separar sinal, confianca e origem.
4. `StrategyDecision` deve ser limitada a um conjunto finito de acoes normalizadas.
5. `LLMDecision` ou equivalente deve ser validavel, auditavel e comparavel com fallback.

## 10. Conclusao

Este projeto pode ser reescrito parcialmente sem perder sua essencia, desde que estas invariantes sejam tratadas como contratos de produto e nao apenas como detalhes do codigo atual.

Resumo:

- o dominio central e defensivo, nao oportunista;
- a IA importa e deve permanecer;
- a confiabilidade importa tanto quanto a precisao;
- o sistema precisa continuar auditavel e orientado a risco.

## 11. Status do Entregavel

- status: `draft-initial`
- pronto para servir como baseline de invariantes da Fase 0
