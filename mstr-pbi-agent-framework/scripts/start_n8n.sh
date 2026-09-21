#!/usr/bin/env bash
# Start local n8n for the MSTR→PBI framework (dev).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="${N8N_USER_FOLDER:-/workspace/.n8n-data}"
mkdir -p "$DATA_DIR" "$ROOT"

cd "$ROOT"
if [[ ! -x "$ROOT/node_modules/.bin/n8n" ]]; then
  npm install n8n@1.82.0 --no-fund --no-audit
fi

export N8N_USER_FOLDER="$DATA_DIR"
export N8N_PORT="${N8N_PORT:-5678}"
export N8N_HOST="${N8N_HOST:-0.0.0.0}"
export N8N_PROTOCOL="${N8N_PROTOCOL:-http}"
export N8N_SECURE_COOKIE="${N8N_SECURE_COOKIE:-false}"
export N8N_DIAGNOSTICS_ENABLED="${N8N_DIAGNOSTICS_ENABLED:-false}"
export N8N_PERSONALIZATION_ENABLED="${N8N_PERSONALIZATION_ENABLED:-false}"
export N8N_VERSION_NOTIFICATIONS_ENABLED="${N8N_VERSION_NOTIFICATIONS_ENABLED:-false}"
export WEBHOOK_URL="${WEBHOOK_URL:-http://127.0.0.1:${N8N_PORT}/}"

echo "Starting n8n on ${N8N_PROTOCOL}://127.0.0.1:${N8N_PORT}"
exec "$ROOT/node_modules/.bin/n8n" start
