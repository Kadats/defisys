# DefiSys V3 - Motor de Trading DeFi Inteligente

**DefiSys** é um sistema de trading automatizado de nível institucional que implementa a filosofia **BTC Standard Lite**: manter Bitcoin por padrão e alavancar estrategicamente em sinais de alta confirmados. Construído com gestão de risco de nível corporativo, machine learning (treinamento walk-forward) e controles adaptativos de volatilidade.

---

## 🎯 Status do Projeto: Fase 8 Concluída ✅

**Arquitetura Atual:** Modular, baseada em API com suporte a Bull, Bear e Sideways markets.
- ✅ **Fase 1-6:** Concluídas (Infraestrutura, ML, Policy Layer).
- ✅ **Fase 7 (Release Gate):** Kill Switch Global e Travas de Capital operacionais.
- ✅ **Fase 8 (Operacional):** Aave Yield Integration e Aggressive Short Strategy implementados.

**ROI OOS (Jun/25 - Abr/26):** +3.56% em Bear Market (vs -31.1% HODL).

---

## 🎯 Visão Geral do Projeto

### Filosofia Central: BTC Standard Lite (Extended)
A estratégia baseia-se em um princípio robusto de preservação e ataque:
- **Estado Padrão:** Manter em BTC (Bull) ou USD/Yield (Bear).
- **Regime Bullish (Alta):** Alavancagem estratégica via Aave + Uniswap v3 LP Ranges.
- **Regime Bearish (Baixa):** Caminho duplo baseado em confiança ML:
  - **High Confidence Drop:** Aggressive Short via empréstimo de BTC na Aave.
  - **Uncertainty/Stable Drop:** Yield passivo em Stablecoins (Aave V3).
- **Regime Sideways:** Farming conservador Delta-Neutral.

### Principais Funcionalidades

#### 🧠 Machine Learning: Walk-Forward (XGBoost)
- **Features de Derivativos:** Integração real de `FundingRate` e `OpenInterest` (Binance Futures) com escalonamento dinâmico.
- **Janela de Treinamento:** Walk-forward com data de corte adaptativa (Fase 7: Junho/2025).
- **Zero Look-Ahead Bias:** Aplicação rigorosa de `shift(1)` em todas as features.

#### 🛡️ Gestão de Risco Institucional (RiskManager V2)
- **Kill Switch Global:** Desalavancagem total e conversão para 100% USD se o Drawdown Global exceder 15% ou Daily exceder 10%.
- **Position Sizing Adaptativo:** Recálculo automático de ordens baseados no saldo real disponível para eliminar falhas de execução.
- **Travas por Regime:** Limites de Drawdown dinâmicos (BEAR: 10% | BULL: 20%).
- **Reserva de Gas:** Proteção de $50 para operações de emergência.

---

## 🏗️ Arquitetura do Sistema: Workflow de Quatro Fases

O DefiSys opera em uma arquitetura **modular e desacoplada**, com fases claramente separadas:

```text
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: COLETA DE DADOS (Automática na inicialização da API)│
│ ─────────────────────────────────────────────────────────── │
│ • Binance: Velas (klines) de BTC/USDT (4h)                  │
│ • Índice Fear & Greed: Sentimento diário                    │
│ • On-Chain: Blockchair (taxas da rede, padrões de tx)       │
│ • Funding Rate: Binance Futures (sentimento de alavancagem) │
│ • Open Interest: Binance Futures (indicador de volatilidade)│
│ • Volatilidade Implícita: Deribit (mercado de opções)       │
│ • Uniswap V3: Dados das pools (liquidez e volumes)          │
│                                                             │
│ ✅ Saída: Banco de dados PostgreSQL com dados atualizados   │
└─────────────────────────────────────────────────────────────┘
                           ⬇️
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: TREINAMENTO DO MODELO (Acionado via API)            │
│ ─────────────────────────────────────────────────────────── │
│ • Carrega dados preparados do banco de dados                │
│ • Aplica split temporal Walk-Forward:                       │
│   - TREINO: Dados até 31/12/2023 (~4 anos)                  │
│   - TESTE: Dados a partir de 01/01/2024 (~2 anos)           │
│ • Treina: XGBClassifier com base em features essenciais     │
│ • Gera: Predições para toda a base histórica                │
│ • Salva: Predições na tabela ml_predictions                 │
│                                                             │
│ ✅ Saída: Predições de ML prontas para simulação            │
└─────────────────────────────────────────────────────────────┘
                           ⬇️
┌─────────────────────────────────────────────────────────────┐
│ FASE 3-4: BACKTESTING & SIMULAÇÃO (Acionado via API)        │
│ ─────────────────────────────────────────────────────────── │
│ • Carrega predições de ML do banco de dados                 │
│ • Aplica a janela temporal (padrão: últimos 30 dias)        │
│ • Executa a TradingEngine (com AccumulatorStrategy / BTCLite)│
│ • Gera: Trades, posições, curvas de capital (equity)        │
│ • Salva: Métricas resumidas no banco de dados               │
│                                                             │
│ ✅ Saída: Relatório completo do backtest com PnL            │
└─────────────────────────────────────────────────────────────┘
```

### Princípios Chave de Design

1. **Backend Inteligente, Frontend "Burro"**
   - Backend (Python/FastAPI): Processa todos os dados de mercado, ML, e a lógica de trading.
   - Frontend (Vue 3/Tailwind): Exibe dados apenas; sem regras de negócio ou cálculos complexos.

2. **Integridade Temporal (Sem Look-Ahead Bias)**
   - Sincronização de Dados: Sempre coleta os dados mais recentes.
   - Treinamento: Apenas dados históricos até a data de corte (ex: 31/12/2023).
   - Teste: Dados após o corte (nunca antes vistos pelo modelo de treinamento).

3. **Cultura de Testes (TDD)**
   - Orientação baseada em testes contínuos; lógica validada em contêineres Docker usando `pytest`.

---

## 💡 A Estratégia: Como o Sistema Ganha Dinheiro

### Máquina de Estados: Regimes de Mercado

#### 1. **NEUTRO (Padrão/Conservador)**
**Condições de Mercado:** O modelo (ML) prevê lateralização ou incerteza.

**Ações:**
- **Manter BTC:** Mantém exposição 100% à valorização a longo prazo do Bitcoin.
- **Farming Conservador:** Se houver dívida, abre posições pequenas na Uniswap v3 (BTC/USD) com ranges baseados em ATR simétricos.
- **Prioridade no Pagamento de Dívida:** Aloca 50% dos lucros para pagar agressivamente qualquer empréstimo pendente na AAVE.
- **Sem Nova Alavancagem:** Não toma novos USD emprestados.

**Objetivo:** Preservar capital, coletar taxas de LP e reduzir despesas com juros.

---

#### 2. **BULLISH (Crescimento Agressivo)**
**Condições de Mercado:** O modelo prevê tendência de alta (>60% de probabilidade) + BTC acima da SMA200 + Fear & Greed > 45.

**Ações:**
- **Ciclo de Alavancagem (Leverage Loop):**
  1. Deposita BTC como colateral na AAVE.
  2. Pega USD emprestado (máx 50% LTV para manter HF > 2.0).
  3. Troca (swap) 50% do USD emprestado por BTC.
  4. Abre posição concentrada na Uniswap v3 (BTC/USD) com **ranges assimétricos de ATR**:
     - Limite Inferior: `preço - (ATR × 10)` (proteção contra volatilidade).
     - Limite Superior: `preço + (ATR × 25)` (espaço para lucro de alta).
- **Entrada Fracionada:** Os empréstimos são feitos em lotes graduais (ex: de $250) para suavizar a execução.
- **Juros Compostos:** As taxas coletadas das posições LP são reinvestidas.

**Objetivo:** Amplificar os ganhos do BTC usando alavancagem enquanto coleta taxas na Uniswap.

---

#### 3. **Mecanismos de Segurança (Sempre Ativos)**
- **Reserva de Gas ($50)** e **Buffer Líquido (20%)**.
- **Piso de Segurança (Health Factor):** Se o HF da AAVE cair abaixo de 1.5:
  1. Fecha todas as posições LP imediatamente.
  2. Paga a dívida para restaurar o HF para > 2.0.
  3. Retorna ao regime NEUTRO.

---

## 🚀 Instalação e Uso

### Pré-requisitos
- **Docker e Docker Compose** (Ambiente Recomendado)
- Opcionalmente para dev local sem docker: **Python 3.12+**, **Poetry**, **Node.js 20+**

### Quick Start com Docker (Recomendado)

A melhor forma de rodar o DefiSys é via Docker, pois todas as dependências complexas de ML (XGBoost) e banco de dados já vêm prontas.

```bash
# 1. Clone o repositório
git clone https://github.com/Kadats/defisys.git
cd defisys

# 2. Configure o ambiente
cp .env.example .env
# Opcional: Adicione chaves de API caso possua.

# 3. Construa e inicie todos os serviços
docker compose up --build -d

# 4. Acompanhe os logs (útil para ver a sincronização da Fase 1):
docker compose logs -f backend

# Endpoints:
# - API (Swagger UI): http://localhost:8000/docs
# - Frontend: http://localhost:5173
```

### Fluxo de Uso via Frontend

1. Acesse o **Frontend** em `http://localhost:5173`.
2. A sincronização (Fase 1) ocorre automaticamente ao iniciar a API.
3. Clique em **"🤖 Treinar Modelo"** e aguarde a conclusão da Fase 2.
4. Clique em **"▶ Simular"** para rodar o backtest dos últimos dias usando as predições geradas (Fases 3-4).
5. O painel será atualizado automaticamente com as métricas e o histórico de negociação.

### Rotas Essenciais da API

```bash
# Fase 1: Sincronização de Dados (Automática)
POST /api/data/sync

# Fase 2: Treinamento de Modelo
POST /api/model/train

# Fase 3-4: Rodar Simulação / Backtest
# Corpo da requisição: {"initial_capital": 1050, "simulation_days": 30}
POST /api/simulation/run

# Checar Resultados e Status
GET /api/simulation/status
GET /api/simulation/summary
GET /api/simulation
```

---

## 🧪 Testes e Desenvolvimento

O projeto defende rigidamente o **TDD (Test-Driven Development)** e conta atualmente com uma suíte de **110 testes automatizados**, assegurando proteção contra regressões em lógicas financeiras críticas, de machine learning e de execução on-chain. Além disso, a nova **Arquitetura por Regime** e o uso do Ensemble para Sizing de Posições (Cautela vs Ganância) garantem que o sistema proteja ativamente o Drawdown em USD durante "Cisnes Negros".

Qualquer alteração deve começar com um teste que falha e passar em ambiente Docker.

```bash
# Executar todos os testes do backend via Docker (Recomendado)
docker compose exec backend pytest tests/ -p no:cacheprovider

# Para testar localmente na máquina host usando Make (caso configurado localmente)
make test
```

### Comandos de Desenvolvimento (Makefile)
Para conveniência, existe um `Makefile` configurado na raiz:
- `make build`: Constrói a stack docker.
- `make up`: Inicia os serviços em background.
- `make test-docker`: Executa a suíte do `pytest` dentro do contêiner.
- `make down`: Desliga os contêineres e limpa os volumes descartáveis.

---

## 📁 Estrutura do Projeto

```text
defisys/
├── backend/
│   ├── src/
│   │   ├── api.py                 # FastAPI main application
│   │   ├── system_runner.py       # Orquestradores das Fases
│   │   ├── core/                  # Engine de trade, gestão de risco, e PnL
│   │   ├── ai/                    # ML (XGBoost), inferências, heurísticas e Agente LLM
│   │   ├── strategies/            # Estratégias (ex: AccumulatorStrategy, BTCLite)
│   │   ├── data/                  # Fontes de API e abstração do PostgreSQL
│   │   └── utils/                 # Funções matemáticas e indicadores
│   ├── Dockerfile                 # Contêiner do Backend
│   └── tests/                     # Suite de testes TDD rigorosa
├── frontend/
│   ├── src/
│   │   ├── App.vue                # Main app shell (Vue 3)
│   │   ├── views/                 # Páginas (Dashboard, Logs, Simulation)
│   │   └── components/            # Gráficos e Cartões
│   ├── package.json               # Dependências NPM (Tailwind, Lightweight-charts)
│   └── Dockerfile                 # Contêiner do Frontend
├── docs/                          # Documentações detalhadas e referências
├── docker-compose.yml             # Orquestração (Frontend, Backend, PostgreSQL)
├── Makefile                       # Comandos úteis
├── pyproject.toml                 # Dependências gerenciadas via Poetry
└── README.md                      # Este arquivo
```

---

## 🤝 Contribuição
Consulte `CONTRIBUTING.md` para diretrizes sobre formatação, testes obrigatórios e fluxo de versionamento. Todas as credenciais e lógicas secretas não devem nunca ser incluídas no versionamento git.

---

## 📄 Licença
Software Proprietário. Todos os direitos reservados.

---

**DefiSys V3** - Trading inteligente com gestão de risco inabalável e uma arquitetura modular moderna. 🚀
