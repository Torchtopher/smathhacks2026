#!/usr/bin/env bash

# Source this file in your shell:
#   source /home/chris/code/ncssm/smathhacks26/command_aliases.sh

SMATHHACKS26_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

alias run_holoocean_api='(cd "$SMATHHACKS26_ROOT/holoocean" && uv run python api.py)'
alias run_backend='(cd "$SMATHHACKS26_ROOT" && docker compose up -d && cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload --env-file $SMATHHACKS26_ROOT/backend/.env)'
alias run_frontend='(cd "$SMATHHACKS26_ROOT/client" && npm run dev)'
alias run_client='(cd "$SMATHHACKS26_ROOT" && uv run python scripts/demo_client.py --loop)'

ask_holo() {
  local agent_index="${1:-}"
  local base_url="${HOLO_API_BASE:-http://localhost:8900}"
  local out_file="${TMPDIR:-/tmp}/holo_latest_agent_${agent_index}.jpg"
  local url

  if [[ "$agent_index" != "-1" && "$agent_index" != "0" && "$agent_index" != "1" ]]; then
    echo "Usage: ask_holo {-1|0|1}" >&2
    return 2
  fi

  url="${base_url%/}/latest.jpg?wait_ms=1500&agent_index=${agent_index}"
  if ! curl -fsS "$url" -o "$out_file"; then
    echo "Failed to fetch image from ${url}" >&2
    return 1
  fi

  echo "Saved image: $out_file"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$out_file" >/dev/null 2>&1 &
  elif command -v open >/dev/null 2>&1; then
    open "$out_file" >/dev/null 2>&1 &
  else
    echo "No image opener found (tried xdg-open/open)." >&2
  fi
}

run_all_services() {
  (cd "$SMATHHACKS26_ROOT" && docker compose up -d) || return 1

  (cd "$SMATHHACKS26_ROOT/holoocean" && uv run python api.py) &
  local holoocean_pid=$!

  (cd "$SMATHHACKS26_ROOT/backend" && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload --env-file $SMATHHACKS26_ROOT/backend/.env) &
  local backend_pid=$!

  (cd "$SMATHHACKS26_ROOT/client" && npm run dev) &
  local frontend_pid=$!

  (cd "$SMATHHACKS26_ROOT" && uv run python scripts/demo_client.py --loop) &
  local client_pid=$!

  echo "Started holoocean=$holoocean_pid backend=$backend_pid frontend=$frontend_pid client=$client_pid"

  cleanup_all_services() {
    kill "$holoocean_pid" "$backend_pid" "$frontend_pid" "$client_pid" 2>/dev/null
    wait "$holoocean_pid" "$backend_pid" "$frontend_pid" "$client_pid" 2>/dev/null
  }

  trap cleanup_all_services INT TERM EXIT
  wait -n "$holoocean_pid" "$backend_pid" "$frontend_pid" "$client_pid"
}

alias run_all='run_all_services'
