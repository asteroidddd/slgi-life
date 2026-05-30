#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-/home/ubuntu/capston}"
STATE_FILE="$ROOT_DIR/backend/apps/public_data/.state/update_all_state.json"
DB_CONTAINER="${DB_CONTAINER:-capston-db}"
DB_USER="${DB_USER:-slgi}"
DB_NAME="${DB_NAME:-slgi}"

service_field() {
  local unit="$1"
  local field="$2"
  systemctl show "$unit" --property="$field" --value 2>/dev/null || true
}

state_value() {
  local key="$1"
  python3 - "$STATE_FILE" "$key" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]
if not path.exists():
    print("")
    raise SystemExit(0)
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)
value = data
for part in key.split("."):
    if not isinstance(value, dict):
        print("")
        raise SystemExit(0)
    value = value.get(part)
if isinstance(value, bool):
    print(str(value).lower())
elif value is None:
    print("")
else:
    print(value)
PY
}

table_count() {
  local table="$1"
  if ! docker inspect "$DB_CONTAINER" >/dev/null 2>&1; then
    echo "db_container_missing"
    return
  fi
  if [[ "$(docker inspect -f '{{.State.Running}}' "$DB_CONTAINER" 2>/dev/null || true)" != "true" ]]; then
    echo "db_container_stopped"
    return
  fi
  docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -Atc \
    "select case when to_regclass('public.${table}') is null then 'missing' else (select count(*)::text from ${table}) end;" \
    2>/dev/null || echo "error"
}

reload_active="$(service_field capston-data-reload.service ActiveState)"
reload_result="$(service_field capston-data-reload.service Result)"
reload_status="$(service_field capston-data-reload.service ExecMainStatus)"
update_active="$(service_field capston-data-update.service ActiveState)"
update_result="$(service_field capston-data-update.service Result)"
timer_active="$(service_field capston-data-update.timer ActiveState)"
timer_enabled="$(systemctl is-enabled capston-data-update.timer 2>/dev/null || true)"
timer_next="$(systemctl list-timers capston-data-update.timer --no-pager --no-legend 2>/dev/null | awk '{print $1, $2, $3, $4}' || true)"

state_status="$(state_value status)"
state_completed="$(state_value completed)"
state_started="$(state_value started_at)"
state_finished="$(state_value finished_at)"
state_stopped="$(state_value stopped_at)"
state_reason="$(state_value reason)"

echo "reload service: active=${reload_active:-unknown} result=${reload_result:-unknown} exit=${reload_status:-unknown}"
echo "daily service: active=${update_active:-unknown} result=${update_result:-unknown}"
echo "daily timer: enabled=${timer_enabled:-unknown} active=${timer_active:-unknown} next=${timer_next:-none}"
echo "state file: $STATE_FILE"
echo "last update: status=${state_status:-missing} completed=${state_completed:-missing} started=${state_started:-missing} finished=${state_finished:-missing}"
if [[ -n "${state_stopped:-}" || -n "${state_reason:-}" ]]; then
  echo "last stop: stopped_at=${state_stopped:-} reason=${state_reason:-}"
fi

echo "table counts:"
for table in adong ldong gu rent_deal rent_deal_cache bus_stop bus_congestion medical_facility store amenity current_adong dashboard_adong_cache; do
  echo "  ${table}: $(table_count "$table")"
done

safe="no"
if [[ "$state_status" == "success" && "$state_completed" == "true" ]]; then
  required_ok="yes"
  for table in adong ldong gu rent_deal bus_stop medical_facility amenity current_adong dashboard_adong_cache; do
    count="$(table_count "$table")"
    if [[ ! "$count" =~ ^[0-9]+$ || "$count" -le 0 ]]; then
      required_ok="no"
    fi
  done
  if [[ "$required_ok" == "yes" ]]; then
    safe="yes"
  fi
fi

echo "safe to enable daily timer: $safe"

if [[ "$safe" == "yes" ]]; then
  exit 0
fi
exit 1

