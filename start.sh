#!/bin/bash
# Deployment Script for Cultural Events RAG Assistant (Unix/Linux/macOS)
#
# Usage:
#   ./start.sh              # Start both API and UI
#   ./start.sh --api-only   # Start only API
#   ./start.sh --ui-only    # Start only UI
#   ./start.sh --check      # Check prerequisites

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
API_PORT="${API_PORT:-8000}"
UI_PORT="${STREAMLIT_PORT:-8501}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}🔍 $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    echo "========================================================================"
    echo "CHECKING PREREQUISITES"
    echo "========================================================================"
    echo

    local checks_passed=true

    # Check Python
    if command -v python3 &> /dev/null; then
        python_version=$(python3 --version | cut -d' ' -f2)
        print_success "Python $python_version"
    else
        print_error "Python 3.11+ not found"
        checks_passed=false
    fi

    # Check Poetry
    if command -v poetry &> /dev/null; then
        poetry_version=$(poetry --version)
        print_success "$poetry_version"
    else
        print_error "Poetry not found"
        checks_passed=false
    fi

    # Check .env file
    if [ -f "$PROJECT_ROOT/.env" ]; then
        print_success ".env file found"

        if grep -q "MISTRAL_API_KEY" "$PROJECT_ROOT/.env"; then
            if ! grep -q "your_mistral_api_key" "$PROJECT_ROOT/.env"; then
                print_success "MISTRAL_API_KEY configured"
            else
                print_warning "MISTRAL_API_KEY is placeholder"
                checks_passed=false
            fi
        else
            print_error "MISTRAL_API_KEY missing"
            checks_passed=false
        fi
    else
        print_error ".env file not found"
        checks_passed=false
    fi

    # Check database
    if [ -f "$PROJECT_ROOT/data/events.db" ]; then
        db_size=$(du -h "$PROJECT_ROOT/data/events.db" | cut -f1)
        print_success "Events database found ($db_size)"
    else
        print_warning "Events database not found"
    fi

    # Check FAISS index
    if [ -f "$PROJECT_ROOT/data/faiss_index/index.faiss" ]; then
        print_success "FAISS index found"
    else
        print_warning "FAISS index not found"
    fi

    echo

    if [ "$checks_passed" = false ]; then
        print_error "Prerequisites check failed"
        exit 1
    fi

    print_success "All prerequisites satisfied!"
}

# Start API server
start_api() {
    echo "========================================================================"
    print_info "Starting API server on port $API_PORT..."
    echo "========================================================================"
    echo

    cd "$PROJECT_ROOT"
    poetry run uvicorn src.api.main:app \
        --host 0.0.0.0 \
        --port "$API_PORT" \
        --reload &

    API_PID=$!

    # Wait for API to be ready
    sleep 3

    if kill -0 $API_PID 2>/dev/null; then
        print_success "API server started: http://localhost:$API_PORT"
        echo "   Swagger docs: http://localhost:$API_PORT/docs"
    else
        print_error "API server failed to start"
        exit 1
    fi
}

# Start Streamlit UI
start_ui() {
    echo "========================================================================"
    print_info "Starting Streamlit UI on port $UI_PORT..."
    echo "========================================================================"
    echo

    cd "$PROJECT_ROOT"
    poetry run streamlit run src/frontend/app.py \
        --server.port "$UI_PORT" \
        --server.address 0.0.0.0 &

    UI_PID=$!

    # Wait for UI to be ready
    sleep 5

    if kill -0 $UI_PID 2>/dev/null; then
        print_success "Streamlit UI started: http://localhost:$UI_PORT"
    else
        print_error "Streamlit UI failed to start"
        exit 1
    fi
}

# Cleanup on exit
cleanup() {
    echo
    echo "========================================================================"
    print_info "Shutting down services..."
    echo "========================================================================"

    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi

    if [ ! -z "$UI_PID" ]; then
        kill $UI_PID 2>/dev/null || true
    fi

    exit 0
}

trap cleanup SIGINT SIGTERM

# Main execution
main() {
    echo "========================================================================"
    echo "CULTURAL EVENTS RAG ASSISTANT - DEPLOYMENT"
    echo "========================================================================"
    echo

    # Parse arguments
    MODE="both"
    CHECK_ONLY=false

    while [ $# -gt 0 ]; do
        case "$1" in
            --api-only)
                MODE="api"
                shift
                ;;
            --ui-only)
                MODE="ui"
                shift
                ;;
            --check)
                CHECK_ONLY=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                echo "Usage: $0 [--api-only|--ui-only|--check]"
                exit 1
                ;;
        esac
    done

    # Check prerequisites
    check_prerequisites

    if [ "$CHECK_ONLY" = true ]; then
        exit 0
    fi

    echo
    echo "========================================================================"
    echo "STARTING SERVICES"
    echo "========================================================================"
    echo

    # Start services based on mode
    case "$MODE" in
        api)
            start_api
            ;;
        ui)
            start_ui
            ;;
        both)
            start_api
            sleep 2
            start_ui
            ;;
    esac

    echo
    echo "========================================================================"
    echo "SERVICES RUNNING"
    echo "========================================================================"
    echo "API: http://localhost:$API_PORT"
    echo "UI:  http://localhost:$UI_PORT"
    echo
    echo "Press Ctrl+C to stop all services"
    echo "========================================================================"
    echo

    # Wait for user interrupt
    wait
}

main "$@"
