#!/bin/zsh
set -euo pipefail

USER_ID="$(id -u)"
APP_URL="${MARKET_STREAM_PUBLIC_URL:-https://www.globalnewsboard.cn}"
LOCAL_URL="${MARKET_STREAM_LOCAL_URL:-http://127.0.0.1:8010/health}"

echo "== LaunchAgents =="
for label in \
  com.newsclassified.marketstream \
  com.newsclassified.tunnel \
  com.newsclassified.keepawake
do
  if launchctl print "gui/${USER_ID}/${label}" >/tmp/"${label}".status 2>/dev/null; then
    state="$( (rg '^[[:space:]]*state = ' /tmp/"${label}".status | sed 's/^[[:space:]]*state = //') || true )"
    pid="$( (rg '^[[:space:]]*pid = ' /tmp/"${label}".status | sed 's/^[[:space:]]*pid = //') || true )"
    echo "${label}: ${state:-unknown} (pid ${pid:-n/a})"
  else
    echo "${label}: not loaded"
  fi
done

echo
echo "== Local health =="
curl -fsS "$LOCAL_URL" || echo "local health check failed"

echo
echo "== Public homepage =="
python3 - <<PY
import urllib.request
try:
    req = urllib.request.Request("${APP_URL}", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        print(f"status={response.status}")
        print(f"content-type={response.headers.get('content-type')}")
except Exception as exc:
    print(f"public homepage check failed: {exc}")
PY

echo
echo "== Sleep assertions =="
pmset -g assertions | rg 'PreventUserIdleSystemSleep|PreventDiskIdle|caffeinate' || true
