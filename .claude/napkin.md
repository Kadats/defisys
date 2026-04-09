# Napkin Runbook

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Execution & Validation (Highest Priority)
1. **[2026-04-09] Prefer the repo automation for remote setup**
   Do instead: use `./setup_cloud.sh` when the goal is provisioning a simple cloud host for this project before inventing a custom bootstrap flow.
2. **[2026-04-09] Oracle Always Free x86 is too small for the target host**
   Do instead: use `VM.Standard.A1.Flex` if staying Always Free is the priority, or use an AMD64 Flex shape only while covered by credits or Pay As You Go.
3. **[2026-04-09] Backend container must stay multi-arch**
   Do instead: avoid hardcoded library paths like `/lib/x86_64-linux-gnu`; use a runtime image that resolves its own libraries on both amd64 and arm64.
4. **[2026-04-09] Backend changes should keep coverage close to the changed path**
   Do instead: run `poetry run pytest tests/ --cov=backend.src` when touching trading, ML, storage, or API behavior.
5. **[2026-04-09] Keep infrastructure additions simple and isolated**
   Do instead: put standalone IaC under `terraform/` with a small variable surface and a short README.

## Domain Behavior Guardrails
1. **[2026-04-09] Production keys must not allow withdrawals**
   Do instead: use API keys with withdrawals disabled and let the backend abort if a risky key reaches production mode.
2. **[2026-04-09] Production RPC requires redundancy**
   Do instead: configure at least primary and secondary RPC endpoints when the target environment is production.
3. **[2026-04-09] Database roles are intentionally separated**
   Do instead: keep `defisys` for historical and training data, `defisys_paper_trading` for paper trades, and `defisys_test` for pytest-only usage.

## Architecture & Code Placement
1. **[2026-04-09] Financial logic belongs in the backend**
   Do instead: keep strategies, risk logic, and financial math in `backend/src/` and use the frontend only for presentation.
2. **[2026-04-09] Pure calculations should stay isolated**
   Do instead: place deterministic math helpers in `backend/src/utils/math/` instead of mixing them into orchestration code.

## User Directives
1. **[2026-04-09] Follow the repo conventions for dependency management**
   Do instead: manage backend packages through Poetry and frontend packages through npm; do not introduce a separate `requirements.txt` workflow.
