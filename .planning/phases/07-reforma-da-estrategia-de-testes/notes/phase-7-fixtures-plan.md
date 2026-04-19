# Fase 7: Plano de Fixtures e Ambiente de Teste

## 1. Objetivo

Este documento define a estrategia de fixtures, ambiente e isolamento da suite de testes.

## 2. Leitura Executiva

Problema principal atual:

- `tests/conftest.py` copia candles da base principal para a base de teste.

Isso e o maior debt estrutural da suite porque:

- reduz reprodutibilidade;
- cria dependencia oculta de ambiente;
- pode mascarar regressao com estado acidental da base real.

## 3. Diagnostico do `conftest.py` Atual

Comportamentos observados:

- sobrescreve `DATABASE_URL` para usar `TEST_DATABASE_URL`;
- captura a URL principal antes da troca;
- conecta na base principal;
- faz `SELECT` de 42 candles;
- popula a base de teste com esses candles;
- trunca algumas tabelas transacionais a cada teste.

Riscos:

- dependência da base principal existir e estar saudavel;
- schema da base principal influencia a suite;
- dataset de teste nao e plenamente conhecido nem congelado;
- suite fica parcialmente dependente do tempo e do ambiente.

## 4. Principios do Novo Modelo

- testes nao devem ler da base principal;
- o dataset de teste deve ser criado localmente e de forma deterministica;
- fixture de sessao prepara ambiente minimo;
- fixture de funcao isola estado mutavel;
- cada camada deve ter o menor ambiente necessario;
- unitario puro nao deve pagar custo de banco.

## 5. Estrategia-Alvo por Camada

## 5.1 Unitarios

Ambiente:

- nenhum banco;
- nenhuma fixture global pesada.

Fixtures esperadas:

- snapshots pequenos de portfolio;
- candles pequenos;
- predictions pequenas;
- responses de LLM controladas.

## 5.2 Integracao com Banco

Ambiente:

- banco de teste dedicado;
- schema controlado;
- dataset sintetico carregado pela suite.

Fixtures esperadas:

- conexao isolada;
- setup de schema minimo;
- seed de dataset pequeno;
- limpeza controlada entre testes.

## 5.3 Integracao de Gateway

Ambiente:

- sem provider real;
- fakes e responses controladas.

Fixtures esperadas:

- payloads de provider;
- respostas de erro, timeout e retry;
- configuracoes por ambiente.

## 5.4 Smoke de API / BFF

Ambiente:

- wiring minimo do app;
- dependencias injetadas de forma controlada;
- sem depender de base principal.

## 6. Substituto Recomendado para o `conftest.py`

Direcao recomendada:

- `tests/conftest.py` fica apenas com fixtures compartilhadas leves e infraestrutura comum;
- seeds de banco ficam isoladas em helpers ou fixtures especificas;
- datasets sinteticos ficam versionados dentro da suite.

Estrutura sugerida:

- `tests/conftest.py`
  - fixtures base e selecao de ambiente
- `tests/fixtures/market.py`
  - candles sinteticos
- `tests/fixtures/predictions.py`
  - predictions sinteticas
- `tests/fixtures/portfolio.py`
  - snapshots de risco e portfolio
- `tests/fixtures/db.py`
  - helpers de schema, seed e cleanup
- `tests/fixtures/llm.py`
  - contexts e respostas normalizadas

## 7. Dataset Base Recomendado

Dataset minimo de mercado:

- candles sinteticos pequenos e validos;
- cobrindo:
  - alta
  - baixa
  - sideways
  - queda brusca
  - recuperacao

Dataset minimo de predicao:

- confianca alta;
- confianca baixa;
- alternancia de sinal;
- cenarios com abstencao.

Dataset minimo de portfolio/risco:

- saudavel;
- drawdown elevado;
- health factor critico;
- kill switch ativo.

## 8. Politica de Limpeza e Isolamento

Regras:

- test de unitario nao usa cleanup de banco;
- test de integracao limpa apenas o que alterou;
- truncation global indiscriminada deve ser evitada onde houver melhor isolamento;
- cada fixture deve deixar claro o que cria e o que destrói.

## 9. Ambientes Recomendados

## 9.1 Ambiente Unitario

- sem DB
- rapido
- deterministico

## 9.2 Ambiente DB Integration

- `defisys_test` ou equivalente
- schema controlado
- sem leitura da base principal

## 9.3 Ambiente Smoke

- app levantado com dependencias controladas
- contratos de interface validos

## 10. O que Nao Deve Permanecer

- copiar candles da base principal;
- fixture de sessao com dependencia temporal ou ambiental;
- fallback silencioso para dados inexistentes;
- limpeza global que mascara testes mal isolados.

## 11. Prioridade de Execucao Futura

P0:

- substituir o seed vindo da base principal;
- introduzir dataset sintetico minimo;
- separar fixtures por categoria.

P1:

- melhorar isolamento de integracao com DB;
- reduzir truncation global;
- padronizar fakes de gateway e LLM.

P2:

- otimizar performance e ergonomia da suite.

## 12. Status do Entregavel

- status: `draft-initial`
- pronto para orientar a reforma do ambiente de testes da Fase 7
- depende da execucao futura para validar custo e ergonomia do novo modelo
