# Plano de Implementação Estratégica DefiSys

## Objetivo

Evoluir o DefiSys para maximizar retorno ajustado a risco em **USD**, com operação mais robusta em bull, bear e sideways market, sem depender de promessas irreais de “zero prejuízo”. O foco passa a ser:

- aumentar patrimônio final em dólar;
- reduzir drawdown e risco de quebra;
- separar claramente estratégia de alta, defesa e baixa;
- só evoluir para modelos mais complexos depois que motor, risco e validação estiverem corretos.

## Decisões já tomadas

- A métrica principal do sistema será **equity final em USD**.
- Métricas secundárias obrigatórias: max drawdown, Sharpe/Sortino, profit factor, win rate, retorno por regime e alpha versus `BTC hold` e `USD cash`.
- O sistema atual **não deve ser tratado como pronto para capital real**.
- A prioridade imediata é **refatorar e validar**, não adicionar rede neural.
- A evolução de modelos seguirá esta ordem: regras + baselines fortes -> ensemble/regime-aware -> somente depois avaliar deep learning.

## Estado atual resumido

- O código atual é majoritariamente orientado a tese long BTC e preservação parcial de capital.
- As estratégias existentes são: `BTCLiteStrategy`, `AccumulatorStrategy`, `SwingUSDStrategy`, `PureSpotStrategy` e `SmartDCAStrategy`.
- Há falhas estruturais no motor e no gerenciamento de risco que invalidam parte da confiança no backtest.
- A avaliação ainda é fraca para tomada de decisão operacional, especialmente para bear market.

## Princípios de execução

- Toda mudança estratégica deve manter compatibilidade com o fluxo atual em `backend/src/system_runner.py`.
- Toda mudança em execução ou risco precisa de testes unitários e backtests reproduzíveis.
- Nenhuma estratégia nova entra em produção sem comparação contra os baselines existentes.
- Resultados sempre devem ser comparados em janela longa e por regime de mercado, nunca só em 30 dias.

## Fase 1: Corrigir segurança do motor [x]

### Objetivo
Eliminar bugs que podem distorcer saldo, risco, health factor ou resultado do backtest.

### Arquivos foco

- `backend/src/core/trading_engine.py`
- `backend/src/core/risk_manager.py`
- `backend/src/strategies/btc_lite.py`
- `tests/test_trading_engine.py`
- `tests/test_risk_manager.py`

### Tarefas

- [x] 1. Corrigir `open_lp` para não consumir caixa se a persistência falhar.
- [x] 2. Corrigir fluxo de rebalanceamento defensivo para usar a mesma ação entre `RiskManager` e `TradingEngine`.
- [x] 3. Implementar de fato os caminhos “usar caixa para reduzir risco” e “repay debt”.
- [x] 4. Corrigir cálculos de health factor que hoje usam saldo errado em pontos críticos do `BTCLiteStrategy`.
- [x] 5. Isolar o motor de banco nos testes para evitar falhas por infraestrutura.

### Critério de aceite

- Nenhum teste de engine depende de banco real.
- Saldo USD, dívida, colateral e posições permanecem consistentes após exceções.
- Suite alvo: `tests/test_trading_engine.py` e `tests/test_risk_manager.py` totalmente verde.

## Fase 2: Corrigir framework de avaliação [x]

### Objetivo
Parar de otimizar estratégias com métricas insuficientes ou janelas enganosas.

### Arquivos foco

- `backend/src/system_runner.py`
- `backend/src/ai/prediction.py`
- `backend/src/data/pipeline.py`
- `backend/src/config.py`
- `backend/src/data/storage/trading_data.py`

### Tarefas

- [x] 1. Unificar a definição do target do modelo entre config, pipeline e documentação.
- [x] 2. Remover dependência de avaliação por `accuracy` como métrica principal.
- [x] 3. Adicionar relatório padrão com:
   - retorno final em USD;
   - retorno anualizado;
   - max drawdown;
   - Sharpe/Sortino;
   - alpha vs BTC hold;
   - alpha vs cash;
   - número de trades;
   - retorno por regime.
- [x] 4. Rodar backtests em múltiplas janelas fixas: bull, bear, sideways e histórico completo.
- [x] 5. Persistir resultados por `run_id` para comparação e auditoria.

### Critério de aceite

- Cada backtest gera um relatório comparável entre estratégias.
- Não existe mais divergência entre target configurado e target real.
- O time consegue responder “essa estratégia ganha em USD onde e por quê?”.

## Fase 3: Reclassificar o papel das estratégias existentes [x]

### Objetivo
Parar de tratar as 5 estratégias como equivalentes e definir o papel exato de cada uma.

### Decisão proposta

- `PureSpotStrategy`: benchmark passivo.
- `SmartDCAStrategy`: benchmark de acumulação simples.
- `AccumulatorStrategy`: estratégia de acumulação de BTC, não estratégia principal de USD.
- `SwingUSDStrategy`: base de preservação/crescimento em dólar, precisa refatoração forte.
- `BTCLiteStrategy`: melhor candidata a virar estratégia principal modular.

### Tarefas

1. Documentar objetivo, regime ideal e risco de cada estratégia.
2. Padronizar interface de saída: regime, ação, sizing, motivo, risco esperado.
3. Remover lógica duplicada entre estratégias e centralizar sizing/risk gates.
4. Garantir que todas possam ser comparadas com os mesmos inputs e métricas.

### Critério de aceite

- Cada estratégia tem mandato claro.
- Não existem estratégias “misturando tudo” sem objetivo mensurável.

## Fase 4: Implementar arquitetura por regime com foco em USD [x]

### Objetivo
Trocar a lógica “uma estratégia tenta resolver tudo” por uma arquitetura com especialização por regime.

### Estratégia-alvo

- **Bull regime:** capturar alta com exposição direcional e alavancagem controlada.
- **Bear regime:** ganhar com queda quando possível ou preservar USD agressivamente quando não houver short seguro.
- **Sideways regime:** extrair carry, mean reversion ou baixa rotação com risco controlado.

### Tarefas

1. Criar classificador de regime: `bull`, `bear`, `sideways`, `uncertain`.
2. Criar policy layer que escolhe qual subestratégia pode operar em cada regime.
3. Definir regras de “abstenção”: se o sinal é fraco, o sistema fica em caixa.
4. Separar sizing da direção: primeiro decidir se opera, depois decidir quanto.

### Critério de aceite

- O sistema não tenta usar o mesmo comportamento em todos os mercados.
- Existe caminho explícito de defesa e/ou ganho em bear market.

## Fase 5: Bear market de verdade [x]

### Objetivo
Fazer o sistema ter tese clara para queda, orientada a USD.

### Opções de implementação

1. **Modo conservador mínimo:** sair para USD e proteger capital.
2. **Modo intermediário:** operar mean reversion ou rallies de alívio com exposição reduzida.
3. **Modo avançado:** permitir short/instrumento inverso, se a infraestrutura e o risco suportarem.

### Recomendação

Implementar em duas etapas:

1. primeiro construir um bear mode forte de preservação em USD;
2. depois avaliar shorting apenas se houver suporte técnico, custos modelados e controles de risco reais.

### Critério de aceite

- Em janelas de bear, a estratégia principal perde menos que BTC hold.
- Idealmente, gera alpha positivo em USD mesmo quando BTC cai.

## Fase 6: Modelagem preditiva [x]

### Objetivo
Evoluir a inteligência sem cair em complexidade prematura.

### Recomendação de roadmap

1. Baselines robustos com regras e thresholds recalibrados.
2. Ensemble simples:
   - modelo de regime;
   - modelo direcional;
   - modelo de sizing/abstenção.
3. Só depois avaliar redes neurais.

### Opinião técnica

No estado atual, **múltiplos modelos simples e especializados** têm melhor relação risco/valor do que uma rede neural única. Deep learning só deve entrar se:

- o dataset ficar maior e mais limpo;
- a validação por regime estiver madura;
- houver evidência de ganho consistente sobre ensemble tabular.

### Critério de aceite

- O ensemble supera baselines simples em USD líquido e drawdown.
- A troca para deep learning só ocorre com evidência, não por preferência.

## Fase 7: Release gate para operação real [x]

### Objetivo
Criar um processo mínimo de segurança antes de qualquer capital relevante.

### Checklist obrigatório

1. Testes unitários verdes.
2. Backtests históricos por regime salvos.
3. Paper trading ou simulação forward por período mínimo definido.
4. Limites de risco por operação, por dia e por drawdown total.
5. Kill switch operacional.
6. Observabilidade de sinais, decisões, sizing e PnL.

### Critério de aceite

- Qualquer agente consegue provar por artefatos por que a estratégia foi liberada.
- Sem isso, o sistema segue em modo de pesquisa.

## Ordem recomendada de execução

1. Fase 1: corrigir motor e risco.
2. Fase 2: corrigir validação e métricas.
3. Fase 3: redefinir mandato das 5 estratégias.
4. Fase 4: implementar arquitetura por regime.
5. Fase 5: bear mode orientado a USD.
6. Fase 6: ensemble de modelos.
7. Fase 7: gate de operação real.

## Entregáveis finais esperados

- motor seguro e testado;
- benchmark comparativo entre as 5 estratégias;
- pipeline de backtest confiável com métricas em USD;
- estratégia principal orientada a regime;
- bear mode utilizável;
- documentação clara de liberação para operação.

## Definição de sucesso

O plano será considerado concluído quando o sistema demonstrar, com evidência reproduzível, que:

- melhora resultado em USD contra benchmarks simples;
- reduz drawdown em bear market;
- tem comportamento consistente por regime;
- consegue ser operado com disciplina de risco e sem dependência de interpretação manual ad hoc.

## Fase 8: Infraestrutura e Melhoria Operacional [x]

### Objetivo
Resolver falhas de dimensionamento de posição que causam abortos desnecessários e introduzir a capacidade do sistema gerar Yield passivo em Stablecoins no protocolo Aave V3.

### Tarefas
- [x] Sizing Proporcional Adaptativo (RiskManager) com ajuste dinâmico em vez de aborto.
- [x] Integração Aave Yield para capital ocioso em bear/uncertain markets.
- [x] Refino de Logs de Capital (formato `[BALANCE_INFO]`).
- [x] TDD para simulação de saldo insuficiente ajustado dinamicamente.

## Fase 8.2: Sensibilidade e Inteligência [x]

### Objetivo
Aumentar a acurácia do modelo através de engenharia de features em derivativos e implementar um RiskManager dinâmico de acordo com o regime de mercado.

### Tarefas
- [x] Engenharia de Features (Derivativos): escalar e criar `oi_change_4h` e `funding_velocity`.
- [x] RiskManager Dinâmico: adaptar os limites de Drawdown de acordo com o regime.
- [x] Teste de Estresse (TDD): verificar o Kill Switch acionado em quedas (BULL vs BEAR).
- [x] Retreino e Validação.

## Fase 8.3: Aggressive Short e Hidratação [x]

### Objetivo
Conectar dados reais de derivativos e implementar a capacidade de lucrar em quedas acentuadas (Short Selling) via empréstimo na Aave.

### Tarefas
- [x] Data Hydration: sync histórico de Funding Rate e Open Interest (Binance Futures).
- [x] TradingEngine: suporte a `open_short` e `close_short` (empréstimo simulado).
- [x] AggressiveShortStrategy: gatilho em Regime BEAR com alta confiança de queda.
- [x] TDD: validação de lucro em cenário de queda de 5%.
- [x] Retreino Final e Validação de ROI (+3.56% no OOS Bear Market).
