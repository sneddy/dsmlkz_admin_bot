#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "${ROOT_DIR}/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${ROOT_DIR}/.env"
  set +a
fi

: "${BOT_TOKEN:?BOT_TOKEN is required}"
: "${WEBHOOK_URL:?WEBHOOK_URL is required (must end with /webhook)}"

echo "Setting webhook to: ${WEBHOOK_URL}"
curl "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}"
