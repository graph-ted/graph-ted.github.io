#!/usr/bin/env bash
# Build the whole site with scripts/build_site.sh (home page, graph-ted-db
# landing page, and the pinned graph-ted-db docs under /graph-ted-db/docs/)
# and serve it on localhost. Nothing here deploys anything.
#
#   scripts/preview.sh            # build, then (re)start the server in the background
#   scripts/preview.sh build      # build only
#   scripts/preview.sh serve      # (re)start the server on the existing build
#   scripts/preview.sh stop       # stop the server started by this script
#   scripts/preview.sh status
#
# Environment (all optional):
#   HOST, PORT        bind address (default 127.0.0.1:8004)
#   BUILD_DIR         output directory (default <repo>/build, gitignored)
#   DB_CHECKOUT       graph-ted-db clone (default <repo>/../graph-ted-db); the docs
#                     come from the commit pinned in sources/graph-ted-db.ref,
#                     not from the checkout's working tree
#   DB_PYTHON         Python with the docs requirements (default $DB_CHECKOUT/.venv/bin/python)
#   DOCS_SITE_URL     site_url for this docs build only (default http://HOST:PORT/graph-ted-db/docs/)
#   DOCS_REF          build the docs from this ref instead of the pin (testing only)
#   STATE_DIR         log and pid location (default $HOME/.graph-ted)
#   LOG_FILE, PID_FILE
#
# The docs are built from a temporary export of the pinned commit with
# site_url overridden, so the checkout itself is never modified.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8004}"
BUILD_DIR="${BUILD_DIR:-$REPO_DIR/build}"
DB_CHECKOUT="${DB_CHECKOUT:-$REPO_DIR/../graph-ted-db}"
DB_PYTHON="${DB_PYTHON:-$DB_CHECKOUT/.venv/bin/python}"
DOCS_SITE_URL="${DOCS_SITE_URL:-http://$HOST:$PORT/graph-ted-db/docs/}"
STATE_DIR="${STATE_DIR:-$HOME/.graph-ted}"
LOG_FILE="${LOG_FILE:-$STATE_DIR/logs/homepage.log}"
PID_FILE="${PID_FILE:-$STATE_DIR/run/homepage.pid}"

build() {
  BUILD_DIR="$BUILD_DIR" DB_CHECKOUT="$DB_CHECKOUT" DB_PYTHON="$DB_PYTHON" \
    DOCS_SITE_URL="$DOCS_SITE_URL" "$REPO_DIR/scripts/build_site.sh"
}

running_pid() {
  [[ -f "$PID_FILE" ]] || return 1
  local pid
  pid="$(cat "$PID_FILE")"
  kill -0 "$pid" 2>/dev/null && echo "$pid"
}

stop() {
  local pid
  if pid="$(running_pid)"; then
    kill "$pid" && echo "stopped pid $pid"
  fi
  rm -f "$PID_FILE"
}

serve() {
  [[ -f "$BUILD_DIR/index.html" ]] || { echo "no build at $BUILD_DIR; run: $0 build" >&2; exit 1; }
  stop
  mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$PID_FILE")"
  setsid nohup python3 -m http.server "$PORT" --bind "$HOST" --directory "$BUILD_DIR" \
    >>"$LOG_FILE" 2>&1 < /dev/null &
  echo $! > "$PID_FILE"
  sleep 1
  if pid="$(running_pid)"; then
    echo "serving http://$HOST:$PORT/ (pid $pid, log $LOG_FILE)"
  else
    echo "server failed to start; see $LOG_FILE" >&2
    exit 1
  fi
}

case "${1:-all}" in
  all) build; serve ;;
  build) build ;;
  serve) serve ;;
  stop) stop ;;
  status) if pid="$(running_pid)"; then echo "running: pid $pid on http://$HOST:$PORT/"; else echo "not running"; exit 1; fi ;;
  *) echo "usage: $0 [all|build|serve|stop|status]" >&2; exit 2 ;;
esac
