# 🛡️ DefiSys: Roadmap para Nível Institucional

Documento de controle de auditoria de risco e arquitetura para implantação em produção.

---

## Nível 1: Auditoria Quantitativa (Risco do Algoritmo)

- [x] **1.1 Zero Look-ahead Bias**: Garantir que o pipeline de ML e cálculo de indicadores (ex: ATR, RSI) utilize estritamente dados de candles já fechados (shift(1) ou equivalente).

- [x] **1.2 Teste de Estresse de Gas/Slippage**: Parametrizar o TradingEngine para simular picos de taxa na rede Ethereum (ex: Gas a $150) e slippage de 2% durante flash crashes.

---

## Nível 2: Auditoria de Infraestrutura (Risco de Execução)

- [ ] **2.1 Resiliência de API e RPC**: Implementar lógica de fallback, timeouts (max 5s) e retries assíncronos para chamadas externas (ex: consultas de preço e integrações com corretoras/DEX).

- [ ] **2.2 Proteção contra MEV**: Estruturar a lógica de execução real de LPs e Swaps utilizando RPCs privados ou proteção de slippage estrita para evitar ataques de Sandwich Bots.

---

## Nível 3: Auditoria Financeira e de Segurança

- [x] **3.1 Global Kill-Switch (Drawdown)**: Desenvolver um serviço independente que trava novas execuções e converte garantias para Stablecoins caso o portfólio sofra queda > 15% em 24h, ignorando a IA. (Concluído: 2026-04-09)

- [ ] **3.2 API Keys e Sandbox**: Isolar ambientes e garantir que as chaves de produção tenham bloqueio total de saque (Withdrawal = False).

- [ ] **3.3 Paper Trading (Forward Testing)**: Conectar o TradingEngine aos WebSockets de mercado em tempo real e registrar operações virtuais no banco de dados por 3 a 6 meses.

---

## Histórico de Alterações

| Data | Evento | Status |
|------|--------|--------|
| 2026-04-09 | Nível 1 revalidado (Verde). Kill-Switch validado em produção. Iniciado Nível 2 (RPC/Resiliência). | ✓ Concluído |
| 2026-03-27 | Aplicado shift(1) em todas as colunas de features no pipeline de dados para eliminar Look-ahead Bias. Incluída SMA_200. | ✓ Concluído |
| 2026-02-27 | Documento criado. Foco inicial no Nível 1. | ✓ Iniciado |

---

## Notas Adicionais

### Próximos Passos Prioritários:
1. Validar zero look-ahead bias na pipeline de indicadores técnicos
2. Definir matriz de teste de estresse para gas e slippage
3. Caracterizar latência de APIs de fornecedores terceirizados

### Estimativa de Esforço por Nível:
- **Nível 1**: 2-3 sprints (análise quantitativa + testes)
- **Nível 2**: 3-4 sprints (resilência + integração de RPCs)
- **Nível 3**: 4-5 sprints (kill-switch + paper trading)

### Critério de Saída (Produção):
- ✅ Todos os itens do Nível 1 validados
- ✅ Todos os itens do Nível 2 implementados e testados
- ✅ Kill-Switch (3.1) funcional em produção
- ✅ 6 meses de paper trading com Sharpe ≥ 1.2
