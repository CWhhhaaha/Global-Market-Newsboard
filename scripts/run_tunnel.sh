#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/logs"

CONFIG_FILE="${HOME}/.cloudflared/config.yml"
TARGET_URL="${MARKET_STREAM_TUNNEL_TARGET_URL:-http://127.0.0.1:8010}"

if [[ -f "$CONFIG_FILE" ]]; then
  exec /opt/homebrew/bin/cloudflared tunnel --config "$CONFIG_FILE" run
fi

exec /opt/homebrew/bin/cloudflared tunnel --url "$TARGET_URL" --no-autoupdate
