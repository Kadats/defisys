# Fase 9: Alinhamento de Docs, Docker e Operacao

## 1. Objetivo

Este documento define o alinhamento final de documentacao, docker, comandos e operacao local.

## 2. Leitura Executiva

O repo hoje ainda carrega sinais fortes de defasagem operacional:

- README fala em estado e rotas antigas;
- `Makefile` mistura comandos e descricoes desatualizadas;
- `docker-compose.yml` ainda aponta para `backend.src.api:app` e contratos antigos;
- `AGENTS.md` do repo descreve o frontend principal como Vue 3 + Vite, mas o frontend real e Next.js.

## 3. Alvos de Alinhamento

## 3.1 README Principal

Precisa refletir:

- arquitetura final;
- frontend oficial;
- pontos de entrada oficiais;
- comandos reais de desenvolvimento;
- diferenca entre backtest, sandbox e paper trading.

## 3.2 Makefile

Precisa refletir:

- backend oficial;
- frontend oficial em Next.js;
- nomes e descricoes corretos dos targets;
- fluxo atual de teste e desenvolvimento.

Ponto observado:

- `run-frontend` ainda aparece descrito como Vue/Vite, mas executa `npm run dev` dentro de `frontend/`.

## 3.3 Docker e Compose

Precisa refletir:

- app backend oficial;
- app frontend oficial;
- health checks coerentes com a API canonica;
- variaveis de ambiente e bancos alinhados ao estado final.

## 3.4 AGENTS e Docs Tecnicas

Precisam refletir:

- stack real do repo;
- modulos centrais reais;
- caminhos de desenvolvimento atuais;
- limites entre legado e arquitetura final.

## 3.5 Runbook Operacional

Direcao recomendada:

- documentar como subir ambiente;
- como rodar testes;
- como validar baseline minima;
- como observar backend, frontend e runtime;
- como diagnosticar falha de cutover.

## 4. Ordem Recomendada de Alinhamento

1. README principal
2. Makefile e comandos oficiais
3. docker-compose e health checks
4. docs tecnicas centrais
5. runbook pos-migracao

## 5. O que Deve Ser Eliminado

- descricoes oficiais que ainda falam em stack errada;
- comandos oficiais com nome ou narrativa antiga;
- docs que vendem mocks ou fases antigas como estado atual;
- divergencia entre o que o repo faz e o que a documentacao promete.

## 6. Status do Entregavel

- status: `draft-initial`
- pronto para orientar o alinhamento final de docs e operacao da Fase 9
- deve ser refinado quando o ponto de entrada oficial estiver definido no cutover
