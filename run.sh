#!/usr/bin/env bash
set -euo pipefail
export DATA_DIR="${DATA_DIR:-/home/ebk/AI.ROVI/Contract Test/data}"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 