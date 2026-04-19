# Fase 8: Checklist de Readiness

## 1. Objetivo

Este documento define o checklist minimo de readiness para evoluir do backtest para paper trading e, no futuro, aproximar o sistema de execucao real.

## 2. Leitura Executiva

O objetivo aqui nao e autorizar execucao real agora. E evitar que o projeto chegue perto disso sem atravessar os gates certos.

## 3. Readiness para Paper Trading

Antes de considerar paper trading pronto para execucao controlada, precisamos ter:

- modelo claro de paper trading definido;
- runtime separado de backtest;
- eventos e snapshots estruturados;
- kill switch operacional;
- health checks e alertas minimos;
- baseline de testes da Fase 7 cobrindo o runtime essencial;
- observabilidade minima da sessao.

## 4. Readiness para Aproximacao de Execucao Real

Antes de qualquer passo rumo a execucao real, precisamos ter:

- paper trading estavel e auditavel;
- politica formal de ambiente e credenciais;
- barreiras de seguranca adicionais;
- trilha minima de auditoria por decisao e ordem;
- readiness operacional documentado;
- sem ambiguidades entre mock, paper e real.

## 5. Checklist por Bloco

## 5.1 Arquitetura

- [ ] Backtest e runtime estao separados.
- [ ] Sandbox nao e confundido com paper trading.
- [ ] Runtime de paper trading tem loop proprio.
- [ ] Fronteira para futuro executor esta documentada.

## 5.2 Risco

- [ ] Kill switch em runtime esta definido.
- [ ] Health factor e drawdown bloqueiam novas ordens.
- [ ] Reserva de gas continua respeitada.
- [ ] Politica de degradacao de dados esta definida.

## 5.3 LLM

- [ ] Contrato do LLM continua valido em runtime.
- [ ] Fallback e auditavel.
- [ ] Resposta invalida nao gera acao livre.
- [ ] Telemetria de fallback esta prevista.

## 5.4 Eventos e Auditoria

- [ ] Eventos canonicos estao definidos.
- [ ] Correlacao decisao -> ordem -> fill esta definida.
- [ ] Snapshots de runtime estao definidos.
- [ ] Alertas criticos geram trilha auditavel.

## 5.5 Observabilidade

- [ ] Runtime expõe estado operacional.
- [ ] Alertas ativos sao visiveis.
- [ ] Snapshot mais recente e consultavel.
- [ ] Degradacao e visivel para operadores.

## 5.6 Testes

- [ ] Baseline minima da Fase 7 cobre runtime essencial.
- [ ] Smoke de API e interface relacionados ao runtime existem.
- [ ] Fluxos de risco critico tem cenarios de ouro.
- [ ] Dependencia da base principal nao existe.

## 5.7 Ambientes e Seguranca

- [ ] Ambiente `paper` continua isolado.
- [ ] Credenciais reais nao sao pressuposto do runtime paper.
- [ ] Rotas e telas distinguem paper de real.
- [ ] Politica de readiness futura esta documentada.

## 6. Sinais de que Ainda Nao Estamos Prontos

- backtest e runtime compartilham fluxo de forma confusa;
- ticker, sandbox ou painel ainda vendem mock como real;
- kill switch nao esta integrado ao loop operacional;
- eventos nao sao correlacionaveis;
- paper trading nao produz trilha auditavel;
- aproximacao de execucao real depende de inferencia manual e nao de checklist objetivo.

## 7. Sinais de que Pode Fazer Sentido Avaliar Executor Separado

- loop de runtime exige concorrencia ou isolamento forte;
- resiliencia do processo principal vira gargalo;
- necessidade de disponibilidade operacional cresce muito;
- observabilidade e controle de falha pedem separacao de responsabilidade;
- pressao tecnica justifica reavaliar linguagem/runtime especializado.

Observacao:

- essa avaliacao nao implica troca imediata de stack;
- apenas define o gatilho para discutir extracao futura.

## 8. Status do Entregavel

- status: `draft-initial`
- pronto para orientar a readiness operacional da Fase 8
- deve ser refinado antes de qualquer passo rumo a runtime mais proximo do real
