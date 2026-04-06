# Napkin Runbook

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Execution & Validation (Highest Priority)
1. **[2026-04-04] Backend changes should be validated with Poetry commands**
   Do instead: run `make test`, `make lint`, and `make format` from the repo root before wrapping backend work.

## Shell & Command Reliability
1. **[2026-04-04] Backend and frontend use different toolchains**
   Do instead: use Poetry commands at the repo root for Python work and `npm` commands inside `frontend/` for Vue work.

## Domain Behavior Guardrails
1. **[2026-04-06] No Bear Market, priorize Yield Delta-Neutro ou Cash; nunca mantenha colateral volátil sem hedge.**
   Do instead: Prioritize stables or cash preservation.
2. **[2026-04-04] Keep trading logic separated from UI**
   Do instead: place strategy, ML, and financial calculations under `backend/src/` and keep `frontend/` limited to display and interaction.

## User Directives
1. **[2026-04-04] Contributor docs should stay concise and repo-specific**
   Do instead: prefer short operational guidance with exact commands and real paths instead of generic policy text.
