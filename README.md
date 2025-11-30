# DefiSys V3 - Intelligent DeFi Trading Engine

**DefiSys** is an institutional-grade automated trading system that implements the **BTC Standard Lite** philosophy: hold Bitcoin by default, leverage strategically on confirmed bullish signals. Built with enterprise-level risk management, walk-forward machine learning, and adaptive volatility controls.

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

#### 💰 Smart Debt Management
- **Accruing Interest Model:** Simulates realistic AAVE borrow APY (e.g., 8% annually).
- **Opportunistic Repayment:** When cash flow exceeds threshold, aggressively pay down debt to reduce interest drag.
- **Leverage Ladder:** Borrows in 25% increments ($250, $500, $750, $1000) to smooth capital deployment.

---

## 🏗️ Architecture (V2)

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
- **Docker** (optional, for production deployment)

### Installation

1. **Clone the repository:**
   ```bash
   git clone --recurse-submodules https://github.com/Kadats/defisys.git
   cd defisys/defisys-strategy
   ```

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Run the system (train model + backtest):**
   ```bash
   make run
   ```
   This will:
   - Collect 5 years of historical data (BTC price, on-chain metrics, volatility).
   - Train ML model on first 3 years.
   - Backtest strategy on last 2 years.
   - Generate `backtest_report.txt` with detailed performance metrics.

### Docker Deployment (Production)

```bash
docker-compose up --build
```
- **API:** `http://localhost:8000`
- **Dashboard:** `http://localhost:3000`

---

## 🧪 Testing

DefiSys maintains a comprehensive test suite (28 tests) covering all critical paths:

```bash
poetry run pytest tests/ -v
```

**Key Test Coverage:**
- `test_trading_engine.py`: Portfolio state, trade execution, PnL calculations.
- `test_heuristics.py`: ML + technical signal validation.
- `test_smart_harvest.py`: Debt repayment logic.
- `test_sma200_feature.py`: Walk-forward ML training.

**Quality Gate:** All tests must pass before deployment.

---

## 📊 Performance Metrics (Historical Backtest)

*Based on 2-year out-of-sample testing (2022-2024):*

| Metric | Value |
|--------|-------|
| **Initial Capital** | $10,000 |
| **Final Value** | $12,551 |
| **Total Return** | +25.51% |
| **Sharpe Ratio** | 1.42 |
| **Max Drawdown** | -18.3% |
| **Win Rate** | 64% |
| **Avg Leverage** | 1.3x |

*Note: Past performance does not guarantee future results. Crypto markets are highly volatile.*

---

## 🔧 Configuration

Key parameters are centralized in `backend/src/config.py`:

```python
# Risk Management
HEALTH_FACTOR_FLOOR: float = 1.5       # Emergency exit threshold
HEALTH_FACTOR_TARGET: float = 2.0      # Target HF after deleveraging
GAS_RESERVE: float = 50.0              # USD kept for transactions
LIQUID_BUFFER_PCT: float = 0.2         # 20% in stablecoins

# Volatility (ATR Multipliers)
ATR_MULTIPLIER_BULLISH_LOWER: float = 10.0   # Downside protection
ATR_MULTIPLIER_BULLISH_UPPER: float = 25.0   # Upside room
ATR_MULTIPLIER_NEUTRAL: float = 20.0         # Symmetric range

# Leverage
MAX_LTV: float = 0.5                   # Borrow up to 50% of collateral
LEVERAGE_LADDER: List[float] = [0.25, 0.50, 0.75, 1.0]

# ML Training
TRAINING_DAYS: int = 1095              # 3 years
TESTING_DAYS: int = 730                # 2 years
```

---

## 🛠️ Development Commands

### Run Backtest
```bash
make run
```

### Run Tests
```bash
make test
```

### Lint Code
```bash
make lint
```

### Format Code
```bash
make format
```

### Clean Build Artifacts
```bash
make clean
```

---

## 📁 Project Structure

```
defisys-strategy/
├── backend/
│   ├── src/
│   │   ├── core/              # Trading Engine, Risk Manager
│   │   ├── ai/                # Prediction, Heuristics
│   │   ├── strategies/        # BTCLiteStrategy
│   │   ├── utils/math/        # Financial calculations
│   │   ├── config.py          # Central configuration
│   │   ├── data_provider.py   # Market data interface
│   │   └── system_runner.py   # Main orchestrator
│   ├── data/                  # SQLite database, CSVs
│   └── logs/                  # Execution logs
├── tests/                     # Unit tests (28 tests)
├── frontend/                  # Streamlit dashboard
├── docs/                      # Additional documentation
├── pyproject.toml             # Poetry dependencies
├── Makefile                   # Development commands
└── README.md                  # This file
```

---

## 🤝 Contributing

See `CONTRIBUTING.md` for guidelines on:
- Code style (Black, isort, pylint).
- Testing requirements (100% pass rate).
- Git workflow (feature branches, PR reviews).

---

## 📄 License

Proprietary software. All rights reserved.

---

## 🙏 Acknowledgments

Built with:
- **scikit-learn** - Machine Learning
- **pandas/numpy** - Data processing
- **FastAPI** - API framework
- **Streamlit** - Dashboard
- **Poetry** - Dependency management

---

## 📧 Contact

For questions or collaboration inquiries, please open an issue on GitHub.

---

**DefiSys V3** - Trading smarter, not harder. 🚀
