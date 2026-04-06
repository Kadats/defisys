# DefiSys V3 - Motor de Trading DeFi Inteligente

**DefiSys** é um sistema de trading automatizado de nível institucional que implementa a filosofia **BTC Standard Lite**: manter Bitcoin por padrão e alavancar estrategicamente em sinais de alta confirmados. Construído com gestão de risco de nível corporativo, machine learning (treinamento walk-forward) e controles adaptativos de volatilidade.

---

## 🎯 Status do Projeto: Fase 2 Concluída ✅

**Arquitetura Atual:** Modular, baseada em API com separação de responsabilidades (Separation of Concerns).
- ✅ **Fase 1 (Coleta de Dados):** Roda automaticamente ao iniciar a API.
- ✅ **Fase 2 (Treinamento do Modelo):** Acionada via endpoint `/api/model/train`.
- ✅ **Fase 3-4 (Simulação/Backtesting):** Acionada via endpoint `/api/simulation/run`.

**Princípio de Arquitetura Inteligente:** O Backend lida com todo o processamento e cálculos; o Frontend serve exclusivamente para exibição.

---

## 🎯 Visão Geral do Projeto

### Filosofia Central: BTC Standard Lite
A estratégia baseia-se em um princípio contrário (contrarian) porém robusto:
- **Estado Padrão:** Manter 100% em BTC (o ativo mais forte a longo prazo).
- **Regime Bullish (Alta):** Quando o modelo de ML confirma uma tendência de alta + alinhamento técnico, toma-se USD emprestado contra o BTC para amplificar ganhos através de posições concentradas de liquidez (LP) na Uniswap v3.
- **Regime Neutro:** Farming conservador com alavancagem mínima, foco no pagamento de dívidas e coleta de taxas.
- **Nunca Operar Vendido (Short) em BTC:** O sistema nunca aposta contra o Bitcoin, apenas modula a intensidade da alavancagem.

### Principais Funcionalidades

#### 🧠 Machine Learning: Walk-Forward (XGBoost)
- **Janela de Treinamento:** 3 anos de dados históricos (1095 dias).
- **Janela de Teste:** 2 anos à frente (730 dias).
- **Zero Viés de Visão de Futuro (Look-Ahead Bias):** O modelo é treinado usando um XGBClassifier apenas com dados passados e testado em dados futuros não vistos.
- **Retreinamento Adaptativo:** Em produção, o modelo pode ser retreinado sob demanda (ex: mensalmente) para se adaptar a mudanças de regime do mercado.

#### 📊 Gestão Dinâmica de Volatilidade (Ranges Baseados em ATR)
- **O Problema:** Ranges fixos de LP (ex: ±30%) são ineficientes. Muito amplos em mercados calmos (baixas taxas), muito estreitos em mercados voláteis (rebalanceamento frequente).
- **A Solução:** Usar o **Average True Range (ATR)** para dimensionar dinamicamente as posições de LP:
  - **Alta Volatilidade → Ranges Mais Amplos:** Proteção contra oscilações violentas de preço.
  - **Baixa Volatilidade → Ranges Mais Estreitos:** Maximização da eficiência na coleta de taxas.
- **Configuração:**
  - Limite Inferior Bullish: `preço_atual - (ATR × 10.0)`
  - Limite Superior Bullish: `preço_atual + (ATR × 25.0)`
  - Neutro Simétrico: `preço_atual ± (ATR × 20.0)`

#### 🛡️ Gestão de Risco Institucional
- **Módulo RiskManager:** Guardião centralizado que aplica restrições rigorosas de segurança:
  - **Monitoramento do Health Factor (Fator de Saúde):** Nunca permite que posições na AAVE fiquem abaixo de um HF de 1.5 (liquidação ocorre em 1.0).
  - **Reserva de Gas:** Mantém sempre $50 em reservas para transações de emergência.
  - **Buffer Líquido (Liquid Buffer):** Mantém 20% do capital em stablecoins para flexibilidade.
  - **Saída de Emergência:** Desalavancagem automática se os limites de risco forem violados.

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
