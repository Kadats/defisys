# 🚀 DefiSys V3: Institutional-Grade DeFi Trading Engine

![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-009688.svg)
![Docker](https://img.shields.io/badge/Docker-Enabled-blue.svg)
![License](https://img.shields.io/badge/License-Proprietary-red.svg)
![Status](https://img.shields.io/badge/Status-Fase%209%20(Resili%C3%AAncia%20Cloud)-green.svg)

**DefiSys** is an institutional-grade automated cryptocurrency trading system implementing the **BTC Standard Lite** philosophy: maintaining long Bitcoin exposure by default and strategically leveraging on confirmed bullish signals. Built with corporate-level risk management, walk-forward machine learning (XGBoost), and adaptive volatility controls.

---

## 📌 Table of Contents
- [🎯 Project Status](#-project-status)
- [🛡️ Institutional Audit & Resilience](#️-institutional-audit--resilience)
- [🏗️ System Architecture](#️-system-architecture)
- [🧠 Core Features](#-core-features)
- [💡 Trading Strategies](#-the-strategies)
- [🚀 Quick Start](#-installation--usage)
- [🔌 API Endpoints](#-essential-api-routes)
- [🧪 Testing & Development](#-tests--development)
- [📁 Project Structure](#-project-structure)

---

## 🎯 Project Status: Phase 9 (Cloud Resilience) 🚀

The project is currently in its final pre-production stage, focusing on high availability and real-time execution.

- **Completed (Phases 1-8):** Core Infrastructure, ML Pipeline, Regime-Aware Policy, Aave Yield, Aggressive Short.
- **Ongoing (Phase 9):** Optimized Docker infrastructure, Automated Health Checks, and Triple-DB Isolation.
- **Institutional Audit:** Level 1 (Zero Look-ahead), Level 2.1 (Multi-RPC Failover), Level 3.1 (Global Kill-Switch), and Level 3.2 (API Keys & Sandbox) are fully **APPROVED**.

**Performance Benchmark:** ROI OOS (Jun/25 - Apr/26): **+3.56%** in Bear Market (vs -31.1% HODL).

---

## 🛡️ Institutional Audit & Resilience

DefiSys is engineered for high-stakes environments with multi-layered protection:

1.  **Zero Look-ahead Bias (Level 1):** Rigorous validation ensuring ML models and technical indicators (ATR, RSI, SMA) strictly use closed-candle data (`shift(1)`).
2.  **Multi-RPC Failover (Level 2.1):** Automated `RPCManager` that switches between prioritized providers (Alchemy, Flashbots, Infura) on failure or timeout (>5s).
3.  **Global Kill-Switch (Level 3.1):** Hard-coded emergency deleveraging and conversion to Stablecoins if Global Drawdown > 15% or Daily Drawdown > 10%.
4.  **API Security & Sandbox (Level 3.2):** Automated API Key permission checks (requires `canWithdraw: False`) and strict environment isolation via `ENVIRONMENT=sandbox`.

---

## 🏗️ System Architecture

DefiSys operates on a **modular, resilient, and data-isolated** architecture:

### Triple Database Isolation
- **`defisys` (Production/History):** Market data for training and verified backtests.
- **`defisys_test` (Testing):** Ephemeral database for the `pytest` suite.
- **`defisys_paper_trading` (Forward Testing):** Isolated virtual trade logs for real-time simulation.

### Operating Modes
- **Backtest (`/api/simulation/*`, `/api/v1/*`)**: historical replay for analysis and strategy evaluation.
- **Sandbox (`/api/sandbox/run`)**: isolated UX lab with mocked behavior for experimentation.
- **Paper Runtime (`/api/paper/runtime/*`)**: operational paper-trading loop with session state, events, and alerts (no real orders).

### Workflow Visualization
```text
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: DATA INGESTION (Automatic on Boot)                 │
│ ─────────────────────────────────────────────────────────── │
│ • Binance: BTC/USDT Klines (4h)                             │
│ • Sentiment: Fear & Greed Index                             │
│ • On-Chain: Network fees & transaction patterns             │
│ • Derivatives: Funding Rate & Open Interest (Futures)       │
│ • DEX: Uniswap V3 Pool Liquidity & Volume                   │
│ ✅ Output: PostgreSQL Hydro-Synced Data                     │
└─────────────────────────────────────────────────────────────┘
                           ⬇️
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: ML MODEL TRAINING (API Triggered)                  │
│ ─────────────────────────────────────────────────────────── │
│ • Walk-Forward Temporal Split (Train: <2024, Test: 2024-26) │
│ • Model: XGBClassifier with Derivative Sensitivity          │
│ • Output: Signal Probability stored in ml_predictions       │
└─────────────────────────────────────────────────────────────┘
                           ⬇️
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3-4: SIMULATION & EXECUTION                           │
│ ─────────────────────────────────────────────────────────── │
│ • Regime Classifier (Bull, Bear, Sideways, Uncertain)       │
│ • TradingEngine: Smart Sizing & Risk Gates                  │
│ • Output: Trade History, Equity Curves, Audit Logs          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 Core Features

### 🧠 Machine Learning: Walk-Forward XGBoost
- **Derivative-Aware:** Integrates real-time `FundingRate` velocity and `OpenInterest` change.
- **Confidence Gates:** Executes only when model probability exceeds calibrated thresholds (default 65%).

### 🛡️ RiskManager V2
- **Adaptive Position Sizing:** Automatically adjusts order sizes based on actual balance to prevent execution errors.
- **Regime-Based Limits:** Dynamic Drawdown caps (e.g., BEAR: 10% limit | BULL: 20% limit).
- **Gas Solvency:** Mandatory $50 reserve kept in USD for emergency closes.

---

## 💡 The Strategies

### 1. **Bullish Regime (Aggressive Growth)**
- **Leverage Loop:** BTC collateral on Aave -> Borrow USD -> Concentrated LP on Uniswap V3.
- **Asymmetric ATR Ranges:** Wide upper bounds to capture upside, tight lower bounds for protection.

### 2. **Bearish Regime (Defensive / Shorting)**
- **Aggressive Short:** High-confidence drop signals trigger BTC borrowing and immediate selling.
- **Aave Yield:** Low-confidence/Uncertain periods move all capital to Aave V3 Lending for passive interest.

---

## 🚀 Installation & Usage

### Prerequisites
- **Docker & Docker Compose** (Highly Recommended)
- Optional: Python 3.12+, Poetry, Node.js 20+

### Quick Start (Docker)
The Docker environment comes pre-configured with all ML dependencies (XGBoost) and the PostgreSQL stack.

```bash
# 1. Clone & Enter
git clone https://github.com/Kadats/defisys.git
cd defisys

# 2. Setup Environment
cp .env.example .env
# Edit .env with your API keys (Gemini, Binance, etc.)

# 3. Boot the System
docker compose up --build -d

# 4. Monitor Logs
docker compose logs -f backend
```

---

## 🔌 Essential API Routes

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/model/train` | Train the XGBoost model using historical data. |
| `POST` | `/api/simulation/run` | Execute backtest (Body: `{"simulation_days": 30}`). |
| `GET` | `/api/simulation/summary` | Retrieve PnL, Drawdown, and Sharpe metrics. |
| `GET` | `/api/system/health` | RPC and backend operational health snapshot. |
| `POST` | `/api/sandbox/run` | Execute sandbox simulation flow (mocked lab mode). |
| `POST` | `/api/paper/runtime/start` | Start paper runtime session. |
| `POST` | `/api/paper/runtime/tick` | Process a market snapshot in paper runtime. |
| `GET` | `/api/paper/runtime/status` | Read current paper runtime status and active alerts. |
| `GET` | `/api/paper/runtime/events` | List recent paper runtime events. |

---

## 🧪 Tests & Development

DefiSys follows strict **TDD (Test-Driven Development)** with over **110+ automated tests**.

```bash
# Run full suite in Docker
docker compose exec backend pytest tests/ -p no:cacheprovider

# Local setup via Makefile
make build
make up-test
```

---

## 📁 Project Structure

```text
defisys/
├── backend/
│   ├── src/
│   │   ├── api.py                 # FastAPI Gateway
│   │   ├── core/                  # Engine, RiskManager, RPCManager
│   │   ├── ai/                    # ML Training & Prediction
│   │   ├── strategies/            # Bull/Bear/Short Logic
│   │   └── data/                  # Storage & API Sources
│   └── tests/                     # TDD Suite (110+ Tests)
├── frontend/                      # Next.js Control Center (Fase 10)
├── docs/                          # Institutional Audit Documentation
├── setup_cloud.sh                 # Cloud Auto-Deployment Script
├── docker-compose.yml             # Triple-DB Infrastructure
└── README.md                      # Professional Overview
```

---

## 🤝 Contributing
Refer to `CONTRIBUTING.md` for style guides and PR protocols. 

## 📄 License
Proprietary Software. All rights reserved.

---
**DefiSys V3** - Unyielding Risk Management. Intelligent Execution. 🚀
are. All rights reserved.

---
**DefiSys V3** - Unyielding Risk Management. Intelligent Execution. 🚀
