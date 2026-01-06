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

# Prefer explicit WEBHOOK_URL, otherwise fall back to Railway-provided domains.
WEBHOOK_URL="${WEBHOOK_URL:-${RAILWAY_STATIC_URL:-${RAILWAY_PUBLIC_DOMAIN:-}}}"
: "${WEBHOOK_URL:?WEBHOOK_URL is required (must end with /webhook)}"
if [[ "${WEBHOOK_URL}" != */webhook ]]; then
  WEBHOOK_URL="${WEBHOOK_URL%/}/webhook"
fi

echo "Setting webhook to: ${WEBHOOK_URL}"
curl "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}"
