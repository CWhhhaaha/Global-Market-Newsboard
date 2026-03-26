#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="${HOME}/Library/Application Support/news_classified"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"

mkdir -p \
  "$APP_DIR" \
  "$APP_DIR/scripts" \
  "$APP_DIR/deploy" \
  "$APP_DIR/logs" \
  "$LAUNCH_AGENTS_DIR"

cp "$PROJECT_DIR/scripts/run_local.sh" "$APP_DIR/scripts/run_local.sh"
cp "$PROJECT_DIR/scripts/run_tunnel.sh" "$APP_DIR/scripts/run_tunnel.sh"
cp "$PROJECT_DIR/scripts/run_keepawake.sh" "$APP_DIR/scripts/run_keepawake.sh"
chmod +x \
  "$APP_DIR/scripts/run_local.sh" \
  "$APP_DIR/scripts/run_tunnel.sh" \
  "$APP_DIR/scripts/run_keepawake.sh"

cp "$PROJECT_DIR/deploy/com.newsclassified.marketstream.plist" \
  "$LAUNCH_AGENTS_DIR/com.newsclassified.marketstream.plist"
cp "$PROJECT_DIR/deploy/com.newsclassified.tunnel.plist" \
  "$LAUNCH_AGENTS_DIR/com.newsclassified.tunnel.plist"
cp "$PROJECT_DIR/deploy/com.newsclassified.keepawake.plist" \
  "$LAUNCH_AGENTS_DIR/com.newsclassified.keepawake.plist"

for label in \
  com.newsclassified.marketstream \
  com.newsclassified.tunnel \
  com.newsclassified.keepawake
do
  echo "Refreshing ${label}..."
  launchctl bootout "gui/$(id -u)/${label}" >/dev/null 2>&1 || true
  sleep 2
  if ! launchctl bootstrap "gui/$(id -u)" "$LAUNCH_AGENTS_DIR/${label}.plist"; then
    echo "Failed to bootstrap ${label}" >&2
    exit 1
  fi
  sleep 1
  launchctl kickstart -k "gui/$(id -u)/${label}" >/dev/null 2>&1 || true
done

echo "Installed and restarted launch agents:"
echo "  - com.newsclassified.marketstream"
echo "  - com.newsclassified.tunnel"
echo "  - com.newsclassified.keepawake"
