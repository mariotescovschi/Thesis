#!/usr/bin/env bash
# Run backend (uvicorn) + frontend (vite) together. Ctrl+C stops both.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
trap 'kill 0' EXIT

( cd "$ROOT/app/backend" && python3 -m uvicorn main:app --reload --port 8000 ) &
( cd "$ROOT/app/frontend" && bun run dev ) &
wait
