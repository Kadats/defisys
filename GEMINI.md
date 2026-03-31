# DefiSys - Project Context for Gemini

## Project Overview

**DefiSys** (version 3) is an institutional-grade automated cryptocurrency trading system that implements the **BTC Standard Lite** philosophy: holding Bitcoin by default and leveraging strategically on confirmed bullish signals. The system uses walk-forward machine learning (XGBoost) and adaptive volatility controls (ATR-based ranges) to manage liquidity positions in DeFi protocols (Uniswap v3, Aave).

The system architecture is strictly split into:
1. **Data Fetching (Phase 1):** Automated collection of market data (Binance, Blockchair, Deribit, Uniswap V3) to a PostgreSQL database.
2. **Model Training (Phase 2):** On-demand walk-forward training using XGBClassifier on historical data without look-ahead bias.
3. **Simulation/Backtesting (Phase 3-4):** Executing trading strategies (e.g., `AccumulatorStrategy`, `BTCLiteStrategy`) against ML predictions and visualizing outcomes.

## Architecture & Core Technologies

This is a modular, API-driven application.

### Backend (`backend/`)
- **Language:** Python 3.12+
- **Dependency Management:** Poetry (`pyproject.toml`)
- **Framework:** FastAPI (`backend/src/api.py`), Uvicorn
- **Database / ORM:** PostgreSQL, SQLAlchemy, Psycopg2
- **Data Science / ML:** Pandas, NumPy, Scikit-learn, XGBoost
- **AI Integration:** Google Generative AI (`google-generativeai`)
- **Structure:**
  - `src/api.py` & `main.py`: Application entrypoints and API endpoints.
  - `src/core/`: Trade execution engine and centralized risk management.
  - `src/ai/`: ML model training, prediction, and heuristics (rule-based signals).
  - `src/strategies/`: Trading strategies logic.
  - `src/data/`: Data pipelines, external API sources, and database storage.
  - `src/utils/math/`: Stateless, testable financial mathematics (APY, IL, Uniswap math).

### Frontend (`frontend/`)
- **Framework:** Vue.js 3 (`App.vue`, `views/`, `components/`)
- **Build Tool:** Vite
- **Styling:** Tailwind CSS, PostCSS
- **Libraries:** Vue Router, Lightweight Charts (for crypto charts), xterm.js (for log terminal)
- **Role:** Exclusively a display layer. "Smart Backend, Dumb Frontend".

### Infrastructure
- **Containerization:** Docker & Docker Compose (`docker-compose.yml`, `Dockerfile`s for both frontend and backend).

## Building and Running

The recommended way to run the application is via Docker:

```bash
# Start all services (Backend, Frontend, PostgreSQL)
docker compose up --build -d

# Check backend logs (to see Phase 1 Data Sync)
docker compose logs -f backend
```

Once running:
- **API:** http://localhost:8000
- **Frontend:** http://localhost:5173

### Local Development (Without Docker)

🚫 AMBIENTE APENAS PARA LEITURA. A execução de testes e lógica depende das bibliotecas do container (XGBoost, FastAPI, etc.) e deve ocorrer via Docker.

**Backend:**
```bash
# Install dependencies
poetry install

# Start API
poetry run uvicorn backend.src.api:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Workflows (API Endpoints)

- **Sync Data:** `POST /api/data/sync` (Usually runs automatically on startup)
- **Train Model:** `POST /api/model/train` (Required before simulation)
- **Run Simulation:** `POST /api/simulation/run` (Payload: `{"initial_capital": 1050, "simulation_days": 30}`)
- **Simulation Status:** `GET /api/simulation/status`
- **Simulation Results:** `GET /api/simulation/summary` or `GET /api/simulation`

## Development Conventions

- **Backend Code Style:** Managed via `ruff` and `black`. Typing via `mypy`.
- **Cultura de Testes (TDD):** Este projeto utiliza estritamente TDD (Test-Driven Development). Nenhuma funcionalidade deve ser implementada antes de seu respectivo teste unitário ou de integração estar escrito e falhando no ambiente Docker. O projeto suporta um banco de dados efêmero para testes (`postgres_test`) para proteger os dados de produção.
- **Backend Testing:** `pytest` is used extensively. Test files are in the `tests/` directory (e.g., `docker compose exec backend pytest tests/ -p no:cacheprovider`). Busque sempre a cobertura máxima. Testes devem cobrir lógica de execução, segurança de margem e cenários de estresse de rede.
- **Separation of Concerns:** Keep complex logic and calculations in the backend (`backend/src/utils/math/` for stateless formulas). The frontend should strictly consume and display API responses.
- **Safety First:** Modifying the `RiskManager` (`backend/src/core/risk_manager.py`) requires extreme caution as it dictates the safety of institutional capital (Health Factors, liquid buffers).
- **Security:** Arquivos `.env` são estritamente proibidos no versionamento (git). Todas as credenciais devem vir apenas do ambiente Docker e nunca devem ser expostas.

## Gemini CLI Rules & Skills

- **Regra 1 (TDD First):** Ao receber uma tarefa de nova feature ou refatoração, seu primeiro passo deve ser planejar e escrever os testes. O ciclo obrigatório é: 1. Escrever o Teste -> 2. Falhar no Docker -> 3. Implementar -> 4. Passar. Só prossiga para o código de produção após os testes existirem.
- **Regra 2 (Ambiente Docker):** Use sempre `docker compose exec backend` para comandos de execução e teste. Nunca tente instalar dependências no host local.
- **Regra 3 (Gestão de Contexto):** Respeite o arquivo `.gemini-ignore` para não ler logs (`*.log`) ou bases de dados (`*.db`), economizando tokens e mantendo o foco no código.