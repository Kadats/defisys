# Repository Guidelines

## Project Structure & Module Organization
`backend/src/` contains the Python application: `api.py` exposes the FastAPI app, `system_runner.py` orchestrates sync, training, and simulation flows, `core/` holds trading and risk logic (including `rpc_manager.py` for Multi-RPC Failover), `ai/` holds ML and sentiment code, `data/` handles ingestion and storage, and `utils/math/` contains pure financial helpers. `frontend/src/` is the Next.js app (`app/`, `components/`, and `hooks/`) acting as UI + BFF proxy layer. `tests/` contains the backend test suite. Supporting docs live in `docs/`, and container setup lives in `docker-compose.yml`, `backend/Dockerfile`, and `frontend/Dockerfile`. The `setup_cloud.sh` script facilitates remote deployment.

## Build, Test, and Development Commands
Use Poetry for backend work and npm for the frontend.

- `make install`: install Python dependencies with Poetry.
- `make install-frontend`: install frontend dependencies with npm.
- `./setup_cloud.sh`: automate Docker installation and basic setup for cloud instances.
- `make run-api`: start FastAPI with reload on `0.0.0.0`.
- `make run-frontend`: run the Next.js frontend locally (`next dev`).
- `cd frontend && npm run dev`: run the Next.js frontend locally.
- `make test` or `poetry run pytest tests/ -v`: run the backend test suite locally.
- `make test-docker`: run the backend suite in Docker through `backend-test`.
- `make up-test`: start the Docker stack and run backend tests in one step.
- `make lint`: run Ruff checks.
- `make format`: run Ruff format and Black.
- `make up` / `make down`: start or stop the Docker stack (including `postgres`, `postgres_test`, and `postgres_paper`).
- `cd frontend && npm run build`: build the Vue app for production.

## Coding Style & Naming Conventions
Target Python 3.12 and keep 4-space indentation. Follow Black formatting and Ruff lint rules before opening a PR. Use `snake_case` for Python modules, functions, and test files; use `PascalCase` for React components. Keep pure calculations in `backend/src/utils/math/` and avoid mixing UI logic into backend strategy code.

## Testing Guidelines
Write backend tests with `pytest`, placing files under `tests/` as `test_<feature>.py`. Prefer focused unit tests for math, strategy, and API behavior, matching the current suite (`test_trading_engine.py`, `test_prediction.py`, `test_api.py`). Run `poetry run pytest tests/ --cov=backend.src` when changing core trading, ML, or storage paths.

## Commit & Pull Request Guidelines
Recent history follows Conventional Commits, for example `feat: ...` and `fix: ...`; keep using that format. Create topic branches such as `feat/<name>` or `fix/<name>` instead of committing to `main`. PRs should include a clear summary, linked issue or task when available, test evidence, and screenshots for frontend changes.

## Security & Configuration Tips
Copy `.env.example` to `.env` for local setup and never commit secrets. Manage backend dependencies only through Poetry; Docker installs from `pyproject.toml` and `poetry.lock`, so do not maintain a separate `requirements.txt` workflow.
