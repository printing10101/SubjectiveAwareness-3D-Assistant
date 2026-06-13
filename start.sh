#!/usr/bin/env bash
# ============================================================
# Cross-Platform System Startup Script - Linux/Mac Version
# Services: Ollama -> FastAPI Backend -> Vite Frontend
# ============================================================

set -euo pipefail

# Configuration
OLLAMA_URL="http://localhost:11434"
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Process IDs for cleanup
OLLAMA_PID=""
BACKEND_PID=""
FRONTEND_PID=""

# Create logs directory
mkdir -p "$LOG_DIR"

# ============================================================
# Color Output Helpers
# ============================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo "========================================"
    echo "  $1"
    echo "========================================"
}

print_ok() {
    echo -e "${GREEN}  [OK]${NC} $1"
}

print_info() {
    echo -e "${BLUE}  [INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}  [WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}  [ERROR]${NC} $1"
}

# ============================================================
# Cleanup Function
# ============================================================
cleanup() {
    print_info "Shutting down services..."
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
    [ -n "$OLLAMA_PID" ] && kill "$OLLAMA_PID" 2>/dev/null || true
    print_info "All services stopped"
    exit 0
}

trap cleanup INT TERM

# ============================================================
# Helper Functions
# ============================================================
check_port() {
    # Returns 0 if port is in use, 1 if free
    lsof -i :"$1" -sTCP:LISTEN >/dev/null 2>&1
}

wait_for_service() {
    local url=$1
    local name=$2
    local max_wait=${3:-30}
    local elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        if curl -s --max-time 3 "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        print_info "  Waiting for $name... (${elapsed}s/${max_wait}s)"
    done
    return 1
}

check_service() {
    local url=$1
    local name=$2

    if curl -s --max-time 3 "$url" >/dev/null 2>&1; then
        print_ok "$name"
    else
        print_error "$name"
    fi
}

# ============================================================
# Detect OS
# ============================================================
print_header "System Startup Script - Linux/Mac"

OS_NAME=$(uname -s)
print_info "Operating System: $OS_NAME"

# ============================================================
# Health Check Mode
# ============================================================
if [ "${1:-}" = "--health" ]; then
    print_header "Health Check"

    print_info "Checking Ollama..."
    check_service "$OLLAMA_URL/api/tags" "Ollama"

    print_info "Checking FastAPI Backend..."
    check_service "$BACKEND_URL/health" "FastAPI"

    print_info "Checking Vite Frontend..."
    check_service "$FRONTEND_URL" "Frontend"

    print_header "Health Check Complete"
    exit 0
fi

# ============================================================
# 1. Detect Environment
# ============================================================
print_info "Detecting environment..."

if command -v ollama >/dev/null 2>&1; then
    print_ok "ollama found in PATH"
else
    print_warn "ollama not found in PATH, checking default install location..."
    if [ -f "$HOME/.ollama/bin/ollama" ]; then
        export PATH="$HOME/.ollama/bin:$PATH"
        print_ok "Found ollama at default location"
    else
        print_error "ollama is not installed. Please install from https://ollama.com"
        exit 1
    fi
fi

if ! command -v python3 >/dev/null 2>&1; then
    print_error "Python 3 is not installed or not in PATH"
    exit 1
fi

if ! command -v node >/dev/null 2>&1; then
    print_error "Node.js is not installed or not in PATH"
    exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
    print_error "curl is not installed or not in PATH"
    exit 1
fi

# ============================================================
# 2. Start Ollama Service
# ============================================================
print_header "Starting Ollama Service"

if check_port 11434; then
    print_ok "Ollama is already running on port 11434"
else
    print_info "Starting Ollama service..."
    ollama serve >"${LOG_DIR}/ollama_${TIMESTAMP}.log" 2>&1 &
    OLLAMA_PID=$!

    if ! wait_for_service "$OLLAMA_URL/api/tags" "Ollama" 30; then
        print_error "Ollama failed to start within 30 seconds"
        print_info "Troubleshooting: Check logs at ${LOG_DIR}/ollama_${TIMESTAMP}.log"
        exit 1
    fi
    print_ok "Ollama service started (PID: $OLLAMA_PID)"
fi
print_info "  Access: $OLLAMA_URL"

# ============================================================
# 3. Start FastAPI Backend
# ============================================================
print_header "Starting FastAPI Backend"

if check_port 8000; then
    print_ok "Backend is already running on port 8000"
else
    print_info "Starting FastAPI backend..."
    cd "${SCRIPT_DIR}/backend"
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info \
        >"${LOG_DIR}/backend_${TIMESTAMP}.log" 2>&1 &
    BACKEND_PID=$!
    cd "$SCRIPT_DIR"

    if ! wait_for_service "$BACKEND_URL/health" "FastAPI Backend" 30; then
        print_error "FastAPI Backend failed to start within 30 seconds"
        print_info "Troubleshooting: Check logs at ${LOG_DIR}/backend_${TIMESTAMP}.log"
        exit 1
    fi
    print_ok "FastAPI Backend started (PID: $BACKEND_PID)"
fi
print_info "  Access: $BACKEND_URL"
print_info "  Health: $BACKEND_URL/health"

# ============================================================
# 4. Start Vite Frontend
# ============================================================
print_header "Starting Vite Frontend"

if check_port 3000; then
    print_ok "Frontend is already running on port 3000"
else
    print_info "Starting Vite dev server..."
    cd "${SCRIPT_DIR}/frontend"
    if [ ! -d "node_modules" ]; then
        print_info "Installing npm dependencies..."
        npm install >"${LOG_DIR}/npm_install_${TIMESTAMP}.log" 2>&1
    fi
    npx vite --port 3000 >"${LOG_DIR}/frontend_${TIMESTAMP}.log" 2>&1 &
    FRONTEND_PID=$!
    cd "$SCRIPT_DIR"

    if ! wait_for_service "$FRONTEND_URL" "Vite Frontend" 30; then
        print_error "Vite Frontend failed to start within 30 seconds"
        print_info "Troubleshooting: Check logs at ${LOG_DIR}/frontend_${TIMESTAMP}.log"
        exit 1
    fi
    print_ok "Vite Frontend started (PID: $FRONTEND_PID)"
fi
print_info "  Access: $FRONTEND_URL"

# ============================================================
# 5. Service Monitor
# ============================================================
print_header "All Services Started - Monitoring"
print_info "Press Ctrl+C to stop monitoring and exit"
print_info "Services:"
print_info "  [Ollama]         $OLLAMA_URL"
print_info "  [FastAPI]        $BACKEND_URL"
print_info "  [Vite Frontend]  $FRONTEND_URL"

while true; do
    sleep 10
    check_service "$OLLAMA_URL/api/tags" "Ollama"
    check_service "$BACKEND_URL/health" "FastAPI"
    check_service "$FRONTEND_URL" "Frontend"
done
