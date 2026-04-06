# Napkin Runbook

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Golden Rule of Simplicity
1. **[2026-04-06] Prioritize explicable models (XGBoost/Ensemble) over black-boxes (Deep Learning) until the superiority of the latter is proven via Sharpe Ratio.**

## Domain Behavior Guardrails
1. **[2026-04-06] No Bear Market, priorize Yield Delta-Neutro ou Cash; nunca mantenha colateral volátil sem hedge.**
   Do instead: Prioritize stables or cash preservation.
2. **[2026-04-04] Keep trading logic separated from UI**
   Do instead: place strategy, ML, and financial calculations under `backend/src/` and keep `frontend/` limited to display and interaction.

## Shell & Command Reliability
1. **[2026-04-04] Backend and frontend use different toolchains**
   Do instead: use Poetry commands at the repo root for Python work and `npm` commands inside `frontend/` for Vue work.
