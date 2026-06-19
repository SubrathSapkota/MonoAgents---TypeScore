#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
PID_FILE="$ROOT/.dev-servers.pid"
LOG_DIR="$ROOT/.dev-logs"

BACKEND_PORT=8000
FRONTEND_PORT=5173

usage() {
  cat <<EOF
Usage: ./dev.sh <command>

Commands:
  start    Start backend and frontend dev servers
  stop     Stop both servers
  restart  Stop then start
  status   Show whether servers are running

URLs:
  Frontend  http://localhost:${FRONTEND_PORT}
  Backend   http://localhost:${BACKEND_PORT}
  API docs  http://localhost:${BACKEND_PORT}/docs
EOF
}

load_env() {
  if [[ -f "$BACKEND_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$BACKEND_DIR/.env"
    set +a
  fi
}

port_pids() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
}

is_running() {
  [[ -n "$(port_pids "$1")" ]]
}

stop_port() {
  local port="$1"
  local pids
  pids="$(port_pids "$port")"
  if [[ -n "$pids" ]]; then
    echo "$pids" | xargs kill 2>/dev/null || true
    sleep 1
    pids="$(port_pids "$port")"
    if [[ -n "$pids" ]]; then
      echo "$pids" | xargs kill -9 2>/dev/null || true
    fi
  fi
}

cmd_stop() {
  echo "Stopping servers..."

  if [[ -f "$PID_FILE" ]]; then
    while IFS= read -r pid; do
      [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi

  stop_port "$BACKEND_PORT"
  stop_port "$FRONTEND_PORT"

  echo "Servers stopped."
}

cmd_start() {
  mkdir -p "$LOG_DIR"

  if is_running "$BACKEND_PORT" || is_running "$FRONTEND_PORT"; then
    echo "Servers already running. Use './dev.sh stop' first or './dev.sh restart'."
    cmd_status
    exit 1
  fi

  if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
    echo "Backend venv not found. Run:"
    echo "  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
  fi

  if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    echo "Frontend dependencies not found. Run:"
    echo "  cd frontend && npm install"
    exit 1
  fi

  load_env

  echo "Starting backend on port ${BACKEND_PORT}..."
  # shellcheck disable=SC1091
  source "$BACKEND_DIR/.venv/bin/activate"
  (
    cd "$BACKEND_DIR"
    export DATABASE_URL="${DATABASE_URL:-mysql+aiomysql://root@localhost/hackathon?charset=utf8mb4}"
    nohup uvicorn app.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" \
      > "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$PID_FILE"
  )

  echo "Starting frontend on port ${FRONTEND_PORT}..."
  (
    cd "$FRONTEND_DIR"
    nohup npm run dev -- --host localhost --port "$FRONTEND_PORT" \
      > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! >> "$PID_FILE"
  )

  sleep 2

  if is_running "$BACKEND_PORT" && is_running "$FRONTEND_PORT"; then
    echo ""
    echo "Servers started."
    echo "  Frontend  http://localhost:${FRONTEND_PORT}"
    echo "  Backend   http://localhost:${BACKEND_PORT}"
    echo "  API docs  http://localhost:${BACKEND_PORT}/docs"
    echo ""
    echo "Logs: $LOG_DIR/"
  else
    echo "Failed to start one or more servers. Check logs in $LOG_DIR/"
    cmd_status
    exit 1
  fi
}

cmd_status() {
  if is_running "$BACKEND_PORT"; then
    echo "Backend:  running (port ${BACKEND_PORT})"
  else
    echo "Backend:  stopped"
  fi

  if is_running "$FRONTEND_PORT"; then
    echo "Frontend: running (port ${FRONTEND_PORT})"
  else
    echo "Frontend: stopped"
  fi
}

case "${1:-}" in
  start)
    cmd_start
    ;;
  stop)
    cmd_stop
    ;;
  restart)
    cmd_stop
    sleep 1
    cmd_start
    ;;
  status)
    cmd_status
    ;;
  *)
    usage
    exit 1
    ;;
esac
