#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
docker compose down
docker volume rm smathhacks2026_pgdata 2>/dev/null || true
docker compose up -d
