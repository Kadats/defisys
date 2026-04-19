#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
FULL_SCAN="${FULL_SCAN:-0}"

echo "Legacy surface audit root: ${ROOT}"
echo

echo "[1/4] frontend-vue-backup presence"
if [[ -d "${ROOT}/frontend-vue-backup" ]]; then
  echo "FOUND: frontend-vue-backup/"
else
  echo "NOT FOUND: frontend-vue-backup/"
fi
echo

echo "[2/4] legacy markers in docs"
if [[ "${FULL_SCAN}" == "1" ]]; then
  rg -n "Vue 3 \\+ Vite|frontend-vue-backup|monolito|legacy|legado" \
    "${ROOT}/README.md" \
    "${ROOT}/AGENTS.md" \
    "${ROOT}/docs" \
    "${ROOT}/plan.md" \
    -S || true
else
  rg -n "Vue 3 \\+ Vite|frontend-vue-backup|monolito|legacy|legado" \
    "${ROOT}/README.md" \
    "${ROOT}/AGENTS.md" \
    "${ROOT}/docs" \
    "${ROOT}/plan.md" \
    -S || true
  echo "(hint: FULL_SCAN=1 for expanded scan including all docs + plan.md)"
fi
echo

echo "[3/4] API concentration check"
if [[ -f "${ROOT}/backend/src/api.py" ]]; then
  app_routes="$( (rg -n '^@app\\.' "${ROOT}/backend/src/api.py" || true) | wc -l | tr -d ' ' )"
  echo "backend/src/api.py contains @app routes: ${app_routes}"
fi
echo

echo "[4/4] interface routers currently available"
find "${ROOT}/backend/src/interfaces/api" -maxdepth 1 -type f -name "*routes.py" | sort

echo
echo "Legacy audit complete."
