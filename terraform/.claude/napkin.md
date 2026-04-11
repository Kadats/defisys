# Napkin Runbook

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Execution & Validation (Highest Priority)
1. **[2026-04-11] Validate OCI cost assumptions against current Oracle docs**
   Do instead: check the live Always Free limits before approving shape, CPU, memory, and storage choices.
2. **[2026-04-11] Treat missing required tfvars as plan blockers**
   Do instead: run `terraform plan -input=false` early so missing OCI credentials and OCIDs fail fast before design review.

## Shell & Command Reliability
1. **[2026-04-11] Prefer direct Terraform commands in repo root**
   Do instead: run `terraform fmt`, `terraform init`, `terraform validate`, and `terraform plan` from the root to keep provider and state paths consistent.

## Domain Behavior Guardrails
1. **[2026-04-11] Public subnet means public attack surface**
   Do instead: keep `22` restricted to a fixed `/32` and expose only `80/443` when the VM is intended to serve traffic directly.

## User Directives
1. **[2026-04-11] Review for Oracle minimum viable machine within Free Tier**
   Do instead: prioritize low-cost OCI shapes and summarize whether resources stay inside Always Free or consume trial credits.
