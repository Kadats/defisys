# Fase 9: Pos-Migracao e Manutencao

## 1. Objetivo

Este documento define o que precisa existir depois do cutover para que a migracao nao termine em regressao cultural para o monolito.

## 2. Leitura Executiva

Encerrar a migracao nao significa “parar de pensar arquitetura”. Significa entrar num regime de manutencao onde:

- os contratos novos continuam sendo a verdade oficial;
- debts residuais ficam visiveis;
- o time nao revive o legado por atalho;
- o sistema volta a evoluir de forma incremental.

## 3. Itens Minimos Pos-Migracao

## 3.1 Observabilidade

Manter visivel:

- estado operacional do backend;
- estado do frontend/BFF;
- estado do runtime paper;
- alertas e degradacoes relevantes;
- resultado da baseline minima.

## 3.2 Governanca de Contratos

Regras:

- novos endpoints nascem nos contratos canonicos;
- novos streams seguem a politica de `source_status`;
- nenhum alias legado volta a nascer por conveniencia;
- mudanca breaking exige decisao explicita.

## 3.3 Governanca de Testes

Regras:

- baseline minima continua gate de mudanca;
- `conftest.py` nao volta a depender da base principal;
- smoke e regressao funcional continuam como parte do fluxo.

## 3.4 Debt Residual

Registrar:

- o que ainda ficou como debt aceitavel;
- o que ficou adiado por custo ou prioridade;
- o que exige reavaliacao futura.

## 3.5 Evolucao Futura

Direcao recomendada:

- continuar evoluindo por contratos e fases pequenas;
- evitar reintroduzir regra em interface;
- avaliar executor isolado so quando houver pressao operacional real;
- manter paper trading, backtest e sandbox semanticamente separados.

## 4. Indicadores de Sucesso da Migracao

Sinais de sucesso:

- backend principal nao depende do antigo monolito;
- frontend consome contratos oficiais;
- smoke e baseline ficam estaveis;
- docs e comandos oficiais batem com a realidade;
- novas mudancas deixam de exigir medo estrutural.

## 5. Indicadores de Regressao Arquitetural

Sinais de alerta:

- novos atalhos em rotas ou BFF;
- reintroducao de fallback enganoso;
- compatibilidade temporaria reaparecendo sem prazo;
- testes verdes sustentados por patching excessivo;
- docs defasando rapidamente do repo.

## 6. Status do Entregavel

- status: `draft-initial`
- pronto para orientar o regime de manutencao pos-migracao
- deve ser refinado quando o cutover real acontecer
