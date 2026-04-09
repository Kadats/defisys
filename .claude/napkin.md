# 📓 Napkin: DefiSys Executive Context

## 🛡️ Critical Domain Guardrails
1. **[2026-04-09] API Safety First:** NEVER operate in `production` with an API Key that has `canWithdraw: True`. The system will automatically abort via `SecurityAuditException`.
2. **[2026-04-09] RPC Resilience:** Production requires at least 2 RPC nodes (Primary + Secondary). Multi-RPC Failover is mandatory for institutional uptime.
3. **[2026-04-09] Database Isolation:** 
   - `defisys`: Historical/Training data only.
   - `defisys_paper_trading`: Isolated virtual trades.
   - `defisys_test`: Ephemeral, for `pytest` only.

## 🚀 Execution Reliability
1. **[2026-04-09] Cloud Deployments:** Use `./setup_cloud.sh` to scaffold remote instances. It ensures Docker, Volumes, and Health Checks are correctly provisioned.
2. **[2026-04-06] Model Choice:** Stick to XGBoost/Ensemble until Deep Learning proves a higher Sharpe Ratio on OOS data.

## 🛠️ Tooling & Architecture
1. **[2026-04-04] Separation of Concerns:** Strategies and financial math live in `backend/src/`. Frontend is exclusively a display layer.
2. **[2026-04-04] TDD Protocol:** Write the test -> Fail in Docker -> Implement -> Pass. No production code without coverage.
