#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${MODEL_URI:-}" ]]; then
  python scripts/setup_model.py --target-dir "${MODEL_LOCAL_PATH:-model/bank_marketing_model}"
fi

exec gunicorn -k uvicorn.workers.UvicornWorker -w "${GUNICORN_WORKERS:-2}" -b "0.0.0.0:${PORT:-8000}" app.main:app
