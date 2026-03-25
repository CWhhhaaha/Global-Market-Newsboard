#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/logs"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt >/dev/null

HOST="${MARKET_STREAM_HOST:-127.0.0.1}"
PORT="${PORT:-${MARKET_STREAM_PORT:-8010}}"

exec uvicorn src.market_stream.app:app --host "$HOST" --port "$PORT"
