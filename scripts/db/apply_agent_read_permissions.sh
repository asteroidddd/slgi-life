#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT_DIR/backend/.env"
DB_CONTAINER="${DB_CONTAINER:-capston-db}"
DB_SUPERUSER="${DB_SUPERUSER:-slgi}"
DB_NAME="${DB_NAME:-slgi}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

read -r AGENT_USER AGENT_PASSWORD <<EOF
$(python3 - "$ENV_FILE" <<'PY'
from pathlib import Path
from urllib.parse import urlparse
import sys

env = {}
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if not line or line.lstrip().startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    env[key.strip()] = value.strip().strip('"').strip("'")

url = env.get("AI_AGENT_DATABASE_URL", "")
if not url:
    raise SystemExit("AI_AGENT_DATABASE_URL is missing")

parsed = urlparse(url)
if not parsed.username or not parsed.password:
    raise SystemExit("AI_AGENT_DATABASE_URL must include username and password")

print(parsed.username, parsed.password)
PY
)
EOF

if [[ ! "$AGENT_USER" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
  echo "Invalid AI agent DB username: $AGENT_USER" >&2
  exit 1
fi

ALLOWED_TABLES=(
  adjacent_adong
  adjacent_gu
  adjacent_ldong
  adong
  adong_population
  bus_congestion
  bus_stop
  business_category
  gu
  gu_metric
  ksci_category
  ldong
  ldong_population
  library
  library_hours
  metric
  nearest_subway_adong
  nearest_subway_ldong
  park
  park_adong
  park_ldong
  rent_deal
  rent_deal_ldong_adong_map
  seoul
  seoul_metric
  store
  subway_congestion
  subway_station
  univ
  univ_adong
  univ_ldong
  amenity
  amenity_adong
  amenity_ldong
  current_adong
  current_gu
  current_ldong
  current_seoul
)

if ! docker inspect "$DB_CONTAINER" >/dev/null 2>&1; then
  echo "DB container not found: $DB_CONTAINER" >&2
  exit 1
fi

if [[ "$(docker inspect -f '{{.State.Running}}' "$DB_CONTAINER")" != "true" ]]; then
  echo "DB container is not running: $DB_CONTAINER" >&2
  exit 1
fi

tmp_sql="$(mktemp)"
trap 'rm -f "$tmp_sql"' EXIT

escaped_password="${AGENT_PASSWORD//\'/\'\'}"

cat > "$tmp_sql" <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$AGENT_USER') THEN
        CREATE ROLE $AGENT_USER LOGIN PASSWORD '$escaped_password';
    ELSE
        ALTER ROLE $AGENT_USER LOGIN PASSWORD '$escaped_password';
    END IF;
END
\$\$;

REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM $AGENT_USER;
REVOKE USAGE ON ALL SEQUENCES IN SCHEMA public FROM $AGENT_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM $AGENT_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE ON SEQUENCES FROM $AGENT_USER;

GRANT CONNECT ON DATABASE $DB_NAME TO $AGENT_USER;
GRANT USAGE ON SCHEMA public TO $AGENT_USER;
SQL

for table in "${ALLOWED_TABLES[@]}"; do
  cat >> "$tmp_sql" <<SQL
DO \$\$
BEGIN
    IF to_regclass('public.$table') IS NOT NULL THEN
        EXECUTE 'GRANT SELECT ON TABLE public.$table TO $AGENT_USER';
    END IF;
END
\$\$;
SQL
done

cat >> "$tmp_sql" <<SQL
ALTER ROLE $AGENT_USER SET statement_timeout = '10min';
ALTER ROLE $AGENT_USER SET idle_in_transaction_session_timeout = '5min';
ALTER ROLE $AGENT_USER SET lock_timeout = '30s';
SQL

docker exec -i "$DB_CONTAINER" psql -U "$DB_SUPERUSER" -d "$DB_NAME" -v ON_ERROR_STOP=1 < "$tmp_sql" >/dev/null

grant_count="$(
  docker exec "$DB_CONTAINER" psql -U "$DB_SUPERUSER" -d "$DB_NAME" -Atc \
    "SELECT count(*) FROM information_schema.role_table_grants WHERE grantee = '$AGENT_USER' AND privilege_type = 'SELECT';"
)"

echo "Applied $AGENT_USER read permissions. select_grants=$grant_count"
