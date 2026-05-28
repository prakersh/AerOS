#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}==> $1${NC}"; }
success() { echo -e "${GREEN}==> $1${NC}"; }
warn()    { echo -e "${YELLOW}==> $1${NC}"; }
error()   { echo -e "${RED}==> ERROR: $1${NC}" >&2; }
step()    { echo -e "  ${GREEN}✓${NC} $1"; }

APP_NAME="AEROS"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/logs"

BACKEND_PORT="${AEROS_PORT:-4040}"
FRONTEND_PORT=5173

load_env() {
    if [ -f "$SCRIPT_DIR/.env" ]; then
        set -a
        source "$SCRIPT_DIR/.env"
        set +a
    fi
}

# WeasyPrint (PO PDF rendering) loads pango/gobject via ctypes. On macOS with
# Homebrew these live in $(brew --prefix)/lib, which is not on the dyld search
# path, so PDF generation fails at runtime. Export the fallback path on Darwin.
setup_native_libs() {
    if [ "$(uname)" = "Darwin" ] && command -v brew &>/dev/null; then
        local brew_lib
        brew_lib="$(brew --prefix)/lib"
        if [ -d "$brew_lib" ]; then
            export DYLD_FALLBACK_LIBRARY_PATH="${brew_lib}:${DYLD_FALLBACK_LIBRARY_PATH:-}"
        fi
    fi
}

cmd_setup() {
    info "$APP_NAME — Setup"

    if ! command -v uv &>/dev/null; then
        error "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi

    info "Installing Python dependencies..."
    cd "$SCRIPT_DIR"
    uv sync --all-extras
    step "Python deps installed"

    if [ -d "$SCRIPT_DIR/frontend" ] && [ -f "$SCRIPT_DIR/frontend/package.json" ]; then
        info "Installing frontend dependencies..."
        cd "$SCRIPT_DIR/frontend"
        if command -v pnpm &>/dev/null; then
            pnpm install
        else
            npm install
        fi
        step "Frontend deps installed"
    fi

    cd "$SCRIPT_DIR"
    if [ ! -f ".env" ]; then
        cp .env.example .env
        warn "Created .env from .env.example — edit it with your API keys"
    fi

    mkdir -p data logs .pids

    info "Running migrations..."
    uv run alembic upgrade head
    step "Database migrated"

    info "Seeding demo data..."
    uv run python -m aeros.seed.dark_store
    step "Demo data seeded"

    success "Setup complete!"
}

cmd_start() {
    load_env
    mkdir -p "$PID_DIR" "$LOG_DIR"

    info "Starting $APP_NAME..."

    info "Starting backend on :$BACKEND_PORT..."
    uv run uvicorn aeros.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload \
        > "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$PID_DIR/backend.pid"
    step "Backend PID $(cat "$PID_DIR/backend.pid")"

    info "Starting Huey worker..."
    uv run python -m aeros.workers.huey_app \
        > "$LOG_DIR/worker.log" 2>&1 &
    echo $! > "$PID_DIR/worker.pid"
    step "Worker PID $(cat "$PID_DIR/worker.pid")"

    if [ -d "$SCRIPT_DIR/frontend" ] && [ -f "$SCRIPT_DIR/frontend/package.json" ]; then
        info "Starting frontend on :$FRONTEND_PORT..."
        cd "$SCRIPT_DIR/frontend"
        if command -v pnpm &>/dev/null; then
            pnpm dev > "$LOG_DIR/frontend.log" 2>&1 &
        else
            npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
        fi
        echo $! > "$PID_DIR/frontend.pid"
        step "Frontend PID $(cat "$PID_DIR/frontend.pid")"
        cd "$SCRIPT_DIR"
    fi

    success "$APP_NAME started!"
    echo ""
    echo -e "  Backend:  ${BOLD}http://localhost:$BACKEND_PORT${NC}"
    echo -e "  Frontend: ${BOLD}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "  API docs: ${BOLD}http://localhost:$BACKEND_PORT/docs${NC}"
    echo ""
}

cmd_stop() {
    info "Stopping $APP_NAME..."
    for pidfile in "$PID_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        pid=$(cat "$pidfile")
        name=$(basename "$pidfile" .pid)
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            step "Stopped $name (PID $pid)"
        fi
        rm -f "$pidfile"
    done
    success "All processes stopped."
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

cmd_test() {
    info "Running test suite..."
    cd "$SCRIPT_DIR"
    uv run pytest "${@:---tb=short -q}"
}

cmd_lint() {
    info "Running linters..."
    cd "$SCRIPT_DIR"
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/
    step "Lint passed"
}

cmd_migrate() {
    info "Creating migration..."
    cd "$SCRIPT_DIR"
    uv run alembic revision --autogenerate -m "${1:-auto migration}"
    step "Migration created. Review alembic/versions/ then run: ./app.sh upgrade"
}

cmd_upgrade() {
    info "Applying migrations..."
    cd "$SCRIPT_DIR"
    uv run alembic upgrade head
    step "Database upgraded"
}

cmd_seed() {
    info "Seeding demo data..."
    cd "$SCRIPT_DIR"
    uv run python -m aeros.seed.dark_store
    step "Seeded"
}

cmd_logs() {
    local service="${1:-backend}"
    tail -f "$LOG_DIR/$service.log"
}

cmd_help() {
    echo -e "${BOLD}$APP_NAME — AI Procurement OS${NC}"
    echo ""
    echo "Usage: ./app.sh <command>"
    echo ""
    echo "Commands:"
    echo "  setup      Install deps, migrate, seed"
    echo "  start      Start all services"
    echo "  stop       Stop all services"
    echo "  restart    Stop + start"
    echo "  test       Run pytest"
    echo "  lint       Run ruff check + format"
    echo "  migrate    Create new alembic migration"
    echo "  upgrade    Apply pending migrations"
    echo "  seed       Re-seed demo data"
    echo "  logs       Tail logs (backend|frontend|worker)"
    echo "  help       This message"
}

setup_native_libs

case "${1:-help}" in
    setup)   cmd_setup ;;
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    test)    shift; cmd_test "$@" ;;
    lint)    cmd_lint ;;
    migrate) shift; cmd_migrate "${1:-}" ;;
    upgrade) cmd_upgrade ;;
    seed)    cmd_seed ;;
    logs)    shift; cmd_logs "${1:-}" ;;
    help)    cmd_help ;;
    *)       error "Unknown command: $1"; cmd_help; exit 1 ;;
esac
