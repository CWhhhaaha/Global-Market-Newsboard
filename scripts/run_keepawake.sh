#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/logs"

# Prevent idle sleep while allowing the display to sleep normally.
exec /usr/bin/caffeinate -i -m
