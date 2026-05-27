#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "Missing required file: $path" >&2
    exit 1
  fi
}

require_file "docker-compose.yml"
require_file "backend/.env"
require_file "frontend/.env"
require_file "scripts/db/apply_agent_read_permissions.sh"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed or not in PATH" >&2
  exit 1
fi

echo "[1/6] Starting database and redis"
docker compose up -d db redis

echo "[2/6] Building backend image"
docker compose build backend

echo "[3/6] Running database migrations"
docker compose run --rm backend python manage.py migrate --noinput

echo "[4/6] Applying AI Agent read-only DB permissions"
scripts/db/apply_agent_read_permissions.sh

echo "[5/6] Starting backend"
docker compose up -d backend

echo "[6/6] Container status"
docker compose ps

echo "Initial setup complete."
