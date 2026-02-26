# DefiSys V3 - Intelligent DeFi Trading Engine

**DefiSys** is an institutional-grade automated trading system that implements the **BTC Standard Lite** philosophy: hold Bitcoin by default, leverage strategically on confirmed bullish signals. Built with enterprise-level risk management, walk-forward machine learning, and adaptive volatility controls.

---

## 🎯 Project Status: Phase 2 Complete ✅

**Current Architecture:** Modular, API-driven with separated concerns
- ✅ **Phase 1 (Data Fetching):** Runs automatically on API startup
- ✅ **Phase 2 (Model Training):** Triggered via `/api/model/train` endpoint
- ✅ **Phase 3-4 (Simulation):** Triggered via `/api/simulation/run` endpoint

**Smart Architecture Principle:** Backend handles all computation; Frontend displays results only.

---

## 🎯 Project Overview

### Core Philosophy: BTC Standard Lite
The strategy is based on a contrarian yet robust principle:
- **Default State:** Hold 100% BTC (the strongest long-term asset).
- **Bullish Regime:** When ML confirms uptrend + technical alignment, borrow USD against BTC to amplify gains via concentrated Uniswap v3 liquidity positions.
- **Neutral Regime:** Conservative farming with minimal leverage, focus on debt repayment and fee collection.
- **Never Short BTC:** The system never bets against Bitcoin, only modulates leverage intensity.

### Key Features

#### 🧠 Walk-Forward Machine Learning
- **Training Window:** 3 years of historical data (1095 days).
- **Testing Window:** 2 years forward (730 days).
- **Zero Look-Ahead Bias:** Model is trained only on past data, tested on unseen future data.
- **Adaptive Retraining:** In production, the model can be retrained monthly to adapt to regime changes.

#### 📊 Dynamic Volatility Management (ATR-Based Ranges)
- **Problem:** Fixed LP ranges (e.g., ±30%) are inefficient. Too wide in calm markets (low fees), too narrow in volatile markets (frequent rebalancing).
- **Solution:** Use **Average True Range (ATR)** to dynamically size LP positions:
  - **High Volatility → Wider Ranges:** Protect against violent price swings.
  - **Low Volatility → Tighter Ranges:** Maximize fee collection efficiency.
- **Configuration:**
  - Bullish Lower Bound: `current_price - (ATR × 10.0)`
  - Bullish Upper Bound: `current_price + (ATR × 25.0)`
  - Neutral Symmetric: `current_price ± (ATR × 20.0)`

#### 🛡️ Institutional Risk Management
- **RiskManager Module:** Centralized guardian that enforces safety constraints:
  - **Health Factor Monitoring:** Never allow AAVE positions below HF 1.5 (liquidation at 1.0).
  - **Gas Reserve:** Always maintain $50 for emergency transactions.
  - **Liquid Buffer:** Keep 20% of capital in stablecoins for flexibility.
  - **Emergency Exit:** Automatic deleveraging if risk thresholds breached.

---

## 🏗️ System Architecture: Four-Phase Workflow

DefiSys operates in a **modular, decoupled** architecture with clearly separated phases:

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: DATA FETCHING (Automatic on API Startup)           │
│ ─────────────────────────────────────────────────────────── │
│ • Binance: BTC/USDT klines (4h candles)                    │
│ • Fear & Greed Index (daily sentiment)                     │
│ • On-Chain: Blockchair (network fees, tx patterns)         │
│ • Funding Rate: Binance Futures (leverage sentiment)       │
│ • Open Interest: Binance Futures (volatility indicator)    │
│ • Implied Volatility: Deribit (options market sentiment)   │
│ • Uniswap V3: Pool data (liquidity & volumes)              │
│                                                             │
│ ✅ Output: PostgreSQL database with fresh market data      │
└─────────────────────────────────────────────────────────────┘
                           ⬇️
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: MODEL TRAINING (Triggered by API endpoint)        │
│ ─────────────────────────────────────────────────────────── │
│ • Load prepared data from database                         │
│ • Apply Walk-Forward temporal split:                       │
│   - TRAIN: Data up to 2023-12-31 (~4 years)               │
│   - TEST: Data from 2024-01-01 onwards (~2 years)         │
│ • Train: XGBClassifier on 6 core features                 │
│ • Generate: Predictions for entire history                │
│ • Save: Predictions to ml_predictions table               │
│                                                             │
│ ✅ Output: ML predictions ready for simulation             │
│ 📊 Metrics: Train accuracy, feature importance             │
└─────────────────────────────────────────────────────────────┘
                           ⬇️
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3-4: BACKTESTING & SIMULATION (Triggered by API)    │
│ ─────────────────────────────────────────────────────────── │
│ • Load ML predictions from database                        │
│ • Apply temporal window (default: last 30 days)           │
│ • Execute TradingEngine with AccumulatorStrategy           │
│ • Generate: Trades, positions, equity curves              │
│ • Save: Summary metrics to database                        │
│                                                             │
│ ✅ Output: Complete backtest report with PnL              │
│ 📊 Metrics: ROI, Sharpe ratio, max drawdown               │
└─────────────────────────────────────────────────────────────┘
```

### API Endpoints

```bash
# Phase 1: Data Synchronization (Automatic)
# Triggered at server startup, can also be called manually
# POST /api/data/sync

# Phase 2: Model Training (Manual)
# Trains XGBClassifier and saves predictions
POST /api/model/train

# Phase 3-4: Run Simulation (Manual)
# Executes backtest using saved ML predictions
POST /api/simulation/run

# Query Results
GET /api/simulation/status         # Check if simulation is running
GET /api/simulation/summary        # Get backtest results
GET /api/simulation                # Detailed breakdown
```

### Key Design Principles

1. **Smart Backend, Dumb Frontend**
   - Backend: All market data, ML training, trading logic
   - Frontend: Display only, no calculations

2. **Temporal Integrity (Zero Look-Ahead Bias)**
   - Data Sync: Fresh market data (always current)
   - Training: Only historical data up to cutoff date (2023-12-31)
   - Testing: Data after cutoff (never seen by training)

3. **Separation of Concerns**
   - Data collection ≠ Model training ≠ Backtesting
   - Each phase can be executed independently
   - Results are persisted to database for reuse

---

## 🏗️ Architecture (V3 - Modular & API-Driven)

DefiSys follows a **clean separation of concerns** with modular, testable components:

```
backend/src/
├── core/
│   ├── trading_engine.py    # Execution engine (positions, PnL, state)
│   └── risk_manager.py       # Safety constraints & emergency protocols
├── ai/
│   ├── prediction.py         # ML model training & inference
│   └── heuristics.py         # Rule-based signals (SMA200, Fear & Greed)
├── strategies/
│   ├── base.py               # Abstract strategy interface
│   └── btc_lite.py           # BTC Standard Lite implementation
├── utils/math/
│   ├── financial.py          # Pure functions (APY, ATR ranges, IL)
│   ├── lending.py            # AAVE-specific calculations
│   └── uniswap.py            # Uniswap v3 math (fees, positions)
├── config.py                 # Centralized configuration
├── data_provider.py          # Market data abstraction layer
└── system_runner.py          # Orchestrator (train → backtest → report)
```

### Module Responsibilities

#### `core/` - Execution Layer
- **TradingEngine:** Manages portfolio state, executes trades, tracks PnL.
- **RiskManager:** Validates every action against safety rules, blocks dangerous operations.

#### `ai/` - Intelligence Layer
- **Prediction:** scikit-learn Random Forest trained on 50+ features (technical indicators, on-chain metrics, volatility).
- **Heuristics:** Combines ML predictions with technical filters (SMA200 crossovers, Fear & Greed Index thresholds).

#### `strategies/` - Business Logic
- **BaseStrategy:** Abstract interface enforcing `execute()` contract.
- **BTCLiteStrategy:** Current production strategy implementing the BTC Standard Lite philosophy.

#### `utils/math/` - Pure Financial Mathematics
- **Stateless functions:** No side effects, fully testable.
- **Examples:** `calculate_apy()`, `calculate_dynamic_range()`, `calculate_impermanent_loss()`, `estimate_uniswap_fees()`.

---

## 💡 The Strategy: How It Makes Money

### State Machine: Three Regimes

#### 1. **NEUTRAL (Default/Conservative)**
**Market Conditions:** ML predicts sideways or uncertain outlook.

**Actions:**
- **Hold BTC:** Keep 100% exposure to Bitcoin's long-term appreciation.
- **Conservative Farming:** If debt exists, open small Uniswap v3 LP positions (BTC/USD) with symmetric ATR-based ranges.
- **Debt Repayment Priority:** Allocate 50% of profits to aggressively pay down any outstanding AAVE loans.
- **No New Leverage:** Do not borrow additional USD.

**Goal:** Preserve capital, collect LP fees, reduce interest expenses.

---

#### 2. **BULLISH (Aggressive Growth)**
**Market Conditions:** ML predicts uptrend (>60% bullish probability) + BTC above SMA200 + Fear & Greed > 45.

**Actions:**
- **Leverage Loop:**
  1. Deposit BTC as collateral in AAVE.
  2. Borrow USD (max 50% LTV to maintain HF > 2.0).
  3. Swap 50% of borrowed USD to BTC.
  4. Open concentrated Uniswap v3 LP (BTC/USD) with **asymmetric ATR ranges**:
     - Lower Bound: `price - (ATR × 10)` (protect against volatility).
     - Upper Bound: `price + (ATR × 25)` (allow upside room).
- **Incremental Deployment:** Borrow in $250 ladders to smooth execution and test waters.
- **Compounding:** LP fee rewards are reinvested into new positions.

**Goal:** Amplify BTC gains via leverage while farming Uniswap fees. If BTC rises 20%, leveraged position gains ~30-40% (minus interest/fees).

---

#### 3. **Safety Mechanisms (Always Active)**
**Regardless of regime:**
- **Gas Reserve:** Maintain $50 in stablecoins for transaction fees.
- **Liquid Buffer:** Keep 20% of capital unlocked for emergencies.
- **Health Factor Floor:** If AAVE HF drops below 1.5, immediately:
  1. Close all LP positions.
  2. Repay debt to restore HF > 2.0.
  3. Return to NEUTRAL regime.
- **Smart Repay Threshold:** If cash balance exceeds $300, use excess to repay debt (reduces interest drag).

---

### Example Scenario: Bullish Trade

**Initial State:**
- Portfolio: $10,000 (100% BTC)
- BTC Price: $60,000
- ATR (4h): $2,500

**Bullish Signal Triggered:**
1. Deposit $10,000 BTC to AAVE.
2. Borrow $5,000 USD (50% LTV, HF = 2.0).
3. Swap $2,500 to BTC (now holding $12,500 BTC + $2,500 USD).
4. Open LP with range:
   - Lower: $60,000 - ($2,500 × 10) = $35,000
   - Upper: $60,000 + ($2,500 × 25) = $122,500
5. Collect 0.3% fees on all trades within range.

**Outcome (BTC +20% to $72,000):**
- BTC Holdings: $12,500 → $15,000
- LP Fees Collected: ~$150 (from volume).
- Interest Paid: ~$50 (AAVE 8% APY over period).
- **Net Gain:** $2,600 (vs $2,000 unlevered) = **30% return**.

---

## 🚀 Setup & Usage

### Prerequisites
- **Python 3.12+**
- **Poetry** (dependency manager)
- **Node.js 20+** (for frontend)
- **Docker & Docker Compose** (recommended)
- **PostgreSQL** (included in docker-compose)

### Quick Start with Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/Kadats/defisys.git
cd defisys

# 2. Create .env file with API keys
cp .env.example .env
# Edit .env and add GEMINI_API_KEY if needed

# 3. Build and start all services
docker compose up --build -d

# 4. Service endpoints will be:
#    - API: http://localhost:8000
#    - Frontend: http://localhost:5173
#    - Database: localhost:5432 (internal)
```

### Workflow: Complete Training & Simulation Cycle

#### Step 1: Verify Data Synchronization (Automatic)
```bash
# When the API starts, Phase 1 runs automatically
# Check the logs:
docker compose logs -f backend | grep "SINCRONIZAÇÃO"

# Expected output:
# 🔄 INICIANDO SINCRONIZAÇÃO DE DADOS DE MERCADO NO STARTUP...
# ✅ SINCRONIZAÇÃO DE DADOS DE MERCADO CONCLUÍDA COM SUCESSO!
```

#### Step 2: Train the ML Model
```bash
# Via cURL:
curl -X POST http://localhost:8000/api/model/train

# Expected response:
# {
#   "status": "completed",
#   "message": "Modelo treinado com sucesso! 597 predições geradas.",
#   "data": {
#     "success": true,
#     "predictions_generated": 597,
#     "total_candles": 18658,
#     "split_date": "2024-01-01",
#     "model_type": "XGBClassifier"
#   }
# }
```

#### Step 3: Run Simulation/Backtest
```bash
# Via cURL:
curl -X POST http://localhost:8000/api/simulation/run \
  -H "Content-Type: application/json" \
  -d '{
    "initial_capital": 1050,
    "simulation_days": 30
  }'

# Or use the Frontend:
# 1. Navigate to http://localhost:5173
# 2. Click "🤖 Treinar Modelo" (wait for completion)
# 3. Click "▶ Simular" (wait for results)
```

#### Step 4: View Results
```bash
# Via API:
curl http://localhost:8000/api/simulation/summary

# Or visit the Frontend Dashboard:
# http://localhost:5173 (auto-updates after simulation)
```

### Local Development Setup

If you prefer local development without Docker:

```bash
# 1. Install dependencies
poetry install

# 2. Set up environment
cp .env.example .env

# 3. Start PostgreSQL (requires local installation)
# macOS: brew install postgresql && brew services start postgresql
# Ubuntu: sudo apt-get install postgresql && sudo service postgresql start

# 4. Create database
createdb defisys

# 5. Run migrations (if applicable)
# [Optional: set up initial schema]

# 6. Start backend API (terminal 1)
poetry run uvicorn backend.src.api:app --reload --port 8000

# 7. Start frontend (terminal 2)
cd frontend && npm run dev  # Runs on http://localhost:5173
```

### Manual Data Synchronization

To manually trigger Phase 1 (data fetching) without waiting for API startup:

```bash
# Via API:
curl -X POST http://localhost:8000/api/data/sync

# This will:
# - Fetch missing klines from Binance
# - Update Fear & Greed Index
# - Collect on-chain metrics
# - Update all indicator tables
# - Return immediately (sync happens in background)
```

---

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific test file
poetry run pytest tests/test_trading_engine.py -v

# Run with coverage
poetry run pytest tests/ --cov=backend.src
```

**Test Suite Coverage:**
- `test_trading_engine.py`: Portfolio state, trade execution, PnL
- `test_prediction.py`: ML model training and inference
- `test_heuristics.py`: Signal generation
- `test_ui.py` (optional): Frontend integration tests

### Frontend Tests
```bash
cd frontend && npm test
```

---

## 📊 Performance Metrics (Historical Backtest V2)

*Based on 2-year out-of-sample testing (2024-2026):*

| Metric | Value |
|--------|-------|
| **Initial Capital** | $1,050 |
| **Final Value** | ~$1,200-1,400 |
| **Total Return** | ~+15% to +35% |
| **Max Drawdown** | ~-12% to -18% |
| **Total Trades** | 40-60 |
| **Win Rate** | 58-65% |
| **Sharpe Ratio** | 0.8-1.2 |

*Note: Past performance does not guarantee future results. Crypto markets are highly volatile. Results depend on market conditions during simulation window.*

---

## 🔧 Configuration

Key parameters are centralized in `backend/src/config.py`:

```python
# Data Collection
DEFAULT_HISTORICAL_DAYS = 1095        # Fetch ~3 years of history
DEFAULT_KLINES_LIMIT = 1000           # Binance API limit per request
DEFAULT_INTERVAL = "4h"               # Timeframe for candles

# ML Training
ML_TRAIN_SPLIT_DATE = "2024-01-01"    # Train/test split point
GEMINI_MODEL = "models/gemini-2.5-flash"  # Default LLM
GEMINI_API_DELAY_SECONDS = 5.0        # Rate limiting (15 RPM max)

# Risk Management
HEALTH_FACTOR_FLOOR = 1.5             # AAVE emergency exit
HEALTH_FACTOR_TARGET = 2.0            # Target after deleveraging
GAS_RESERVE = 50.0                    # USD for transactions
LIQUID_BUFFER_PCT = 0.2               # Stablecoin reserves

# Backtesting
GEMINI_BACKTEST_DAYS = 30             # Default simulation window
```

---

## 🛠️ Development Commands

---

## 📁 Project Structure

```
defisys/
├── backend/
│   ├── src/
│   │   ├── api.py                 # FastAPI main application
│   │   ├── main.py                # Entry point (can run simulation manually)
│   │   ├── system_runner.py       # Phase orchestrators
│   │   │   ├── sync_market_data()      # Phase 1: Data fetching
│   │   │   ├── train_model_pipeline()  # Phase 2: ML training
│   │   │   ├── run_simulation()        # Phase 3-4: Backtesting
│   │   │   └── run_trading_system()    # Legacy: all phases together
│   │   ├── core/
│   │   │   ├── trading_engine.py  # Trade execution, PnL, position management
│   │   │   └── risk_manager.py    # Safety constraints, health factor monitoring
│   │   ├── ai/
│   │   │   ├── prediction.py      # XGBClassifier training & inference
│   │   │   ├── llm_agent.py       # Gemini API integration
│   │   │   └── heuristics.py      # Rule-based signals
│   │   ├── strategies/
│   │   │   ├── base.py            # Abstract strategy interface
│   │   │   ├── accumulator.py     # Current production strategy
│   │   │   └── btc_lite.py        # Legacy strategy
│   │   ├── data/
│   │   │   ├── pipeline.py        # Data orchestration (Phase 1)
│   │   │   ├── sources.py         # External API clients
│   │   │   ├── storage.py         # PostgreSQL operations
│   │   │   ├── storage.py         # PostgreSQL DDL & DML
│   │   │   └── sync_market_data() # Automated data synchronization
│   │   ├── services/
│   │   │   └── analytics.py       # Calculation helpers
│   │   ├── utils/
│   │   │   ├── indicators.py      # Technical indicator calculations
│   │   │   ├── log_handler.py     # Logging configuration
│   │   │   └── math/
│   │   │       ├── financial.py   # APY, ROI, token metrics
│   │   │       ├── lending.py     # AAVE-specific calculations
│   │   │       └── uniswap.py     # Uniswap v3 LP math
│   │   ├── config.py              # Centralized configuration
│   │   └── logging_config.py      # Logging setup
│   ├── entrypoint.sh              # Docker entrypoint
│   ├── Dockerfile                 # Container definition
│   ├── data/                      # Database files (PostgreSQL)
│   └── logs/                      # Execution logs
├── frontend/
│   ├── src/
│   │   ├── App.vue                # Main app shell
│   │   ├── views/
│   │   │   ├── DashboardView.vue  # KPI display
│   │   │   ├── SimulationView.vue # Model training & simulation UI
│   │   │   └── LogsView.vue       # System logs
│   │   ├── components/
│   │   │   ├── StatCard.vue       # KPI cards
│   │   │   ├── TradesTable.vue    # Trade history
│   │   │   └── others...
│   │   ├── router/                # Vue routing
│   │   └── style.css              # Global styles
│   ├── index.html                 # HTML entry
│   ├── vite.config.js             # Vite build config
│   ├── package.json               # NPM dependencies
│   └── Dockerfile                 # Frontend container
├── tests/
│   ├── test_trading_engine.py     # Engine tests
│   ├── test_prediction.py         # ML tests
│   ├── test_gemini_unit.py        # LLM tests
│   └── others...
├── docs/
│   ├── ARCHITECTURE_COMPARISON.md # V2 vs V3
│   └── others...
├── docker-compose.yml             # Multi-container orchestration
├── Makefile                       # Development commands
├── pyproject.toml                 # Poetry dependencies
├── poetry.lock                    # Locked dependency versions
│ .env.example                     # Environment template
└── README.md                      # This file
```

### Directory Organization Rationale

| Directory | Responsibility | Phase |
|-----------|-----------------|-------|
| `data/` | API clients, database ops, data orchestration | Phase 1 |
| `ai/` | ML training, predictions, decision logic | Phase 2 |
| `core/` | Trade execution, risk validation | Phase 3-4 |
| `strategies/` | Business logic (when to trade) | Phase 3-4 |
| `utils/` | Pure functions, no side effects | All phases |
| `frontend/` | Display only, UI logic | All phases |

---

## 🌐 API Documentation

### Authentication
Currently, the API has no authentication (suitable for local/private deployment).

### Endpoints

#### Data Synchronization (Phase 1)
```
POST /api/data/sync
Description: Manually trigger market data synchronization
Response: { "status": "complete", "records_updated": 150 }
```

#### Model Training (Phase 2)
```
POST /api/model/train
Description: Train XGBClassifier on historical data
Response: {
  "status": "completed",
  "message": "Modelo treinado com sucesso! 597 predições geradas.",
  "data": {
    "success": true,
    "total_candles": 18658,
    "predictions_generated": 597,
    "split_date": "2024-01-01",
    "model_type": "XGBClassifier"
  }
}
```

#### Run Simulation (Phase 3-4)
```
POST /api/simulation/run
Request Body: {
  "initial_capital": 1050,
  "simulation_days": 30,
  "start_date": null,           // Optional: ISO format
  "end_date": null              // Optional: ISO format
}
Response: {
  "status": "started",
  "message": "Simulação iniciada em background..."
}

Error (400): {
  "detail": "Modelo não treinado. Por favor, execute o treinamento antes de simular."
}
```

#### Check Simulation Status
```
GET /api/simulation/status
Response: {
  "running": false,
  "has_results": true,
  "trades_count": 42
}
```

#### Get Detailed Results
```
GET /api/simulation/summary
Response: {
  "spot": {
    "usd_available": 123.45,
    "btc_balance": 0.021,
    "total_usd": 1234.56
  },
  "defi": { "capital_allocated": 0, ... },
  "aave": { "collateral_btc_usd": 0, ... },
  ...
}

GET /api/simulation
Response: {
  "kpis": { "total_trades": 42, "roi": 15.3, ... },
  "trades": [
    {
      "timestamp": "2026-02-01T12:34:56",
      "side": "BUY",
      "quantity": 0.01,
      "price": 65000,
      ...
    },
    ...
  ]
}
```

---

## 🤝 Contributing

See `CONTRIBUTING.md` for guidelines on:
- Code style (Black, isort, pylint)
- Testing requirements (all tests must pass)
- Git workflow (feature branches, PR reviews)
- Commit message conventions

---

## 📄 License

Proprietary software. All rights reserved.

---

## 🪛 Troubleshooting

### API won't start
```bash
# Check if PostgreSQL is running
docker compose logs postgres

# Restart services
docker compose down && docker compose up --build -d

# Check logs
docker compose logs -f backend
```

### Model training fails
```bash
# Ensure Phase 1 completed (data exists in database)
# Check logs for API errors
docker compose logs backend | grep "ERROR"

# Manually trigger data sync
curl -X POST http://localhost:8000/api/data/sync
```

### Frontend doesn't connect to API
```bash
# Verify API is running on port 8000
curl http://localhost:8000/api/simulation/status

# Check frontend logs
docker compose logs frontend
```

---

## 📧 Contact

For questions or collaboration inquiries, please open an issue on GitHub.

---

**DefiSys V3** - Intelligent trading with modular, API-first architecture. 🚀
