#!/usr/bin/env bash
set -euo pipefail

# Ensure secrets folder exists and has the JSON
if [ ! -f "./secrets/service-account.json" ]; then
  echo "Missing ./secrets/service-account.json"
  exit 1
fi

docker rm -f unlock-schedule >/dev/null 2>&1 || true

APP_VERSION="${APP_VERSION:-latest}"

docker run -d \
  --name unlock-schedule \
  -p 8000:8000 \
  -e DEFAULT_TIMEZONE="America/New_York" \
  -e CALENDAR_ID="${CALENDAR_ID:-primary}" \
  -e GCAL_SERVICE_ACCOUNT_JSON="/secrets/service-account.json" \
  -e GCAL_DELEGATE="" \
  -v "$(pwd)/secrets:/secrets:ro" \
  --read-only \
  --tmpfs /tmp \
  --restart unless-stopped \
  "unlock-schedule:${APP_VERSION}"
