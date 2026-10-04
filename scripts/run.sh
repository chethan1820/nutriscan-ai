#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════
# NutriScan AI — Quick Start Script
# Usage: bash scripts/run.sh [dev|prod|docker|train|eval]
# ══════════════════════════════════════════════════════════

set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

MODE=${1:-dev}

# ── Colors ─────────────────────────────────────────────────
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $1"; }
success() { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }

# ── Banner ──────────────────────────────────────────────────
echo -e "${GREEN}"
echo "  ███╗   ██╗██╗   ██╗████████╗██████╗ ██╗███████╗ ██████╗ █████╗ ███╗   ██╗"
echo "  ████╗  ██║██║   ██║╚══██╔══╝██╔══██╗██║██╔════╝██╔════╝██╔══██╗████╗  ██║"
echo "  ██╔██╗ ██║██║   ██║   ██║   ██████╔╝██║███████╗██║     ███████║██╔██╗ ██║"
echo "  ██║╚██╗██║██║   ██║   ██║   ██╔══██╗██║╚════██║██║     ██╔══██║██║╚██╗██║"
echo "  ██║ ╚████║╚██████╔╝   ██║   ██║  ██║██║███████║╚██████╗██║  ██║██║ ╚████║"
echo "  ╚═╝  ╚═══╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝"
echo "                      AI Food Health Monitoring System v1.0"
echo -e "${NC}"

# ── Setup ───────────────────────────────────────────────────
setup_env() {
    info "Setting up environment..."

    if [ ! -f ".env" ]; then
        cp .env.example .env
        warn "Created .env from .env.example — please review settings"
    fi

    if [ ! -d "venv" ]; then
        info "Creating virtual environment..."
        python3 -m venv venv
    fi

    source venv/bin/activate
    info "Installing dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt

    mkdir -p logs uploads models dataset backend/uploads
    success "Environment ready"
}

# ── Development Mode ────────────────────────────────────────
run_dev() {
    setup_env
    info "Starting development server at http://localhost:5000"
    export FLASK_ENV=development
    export FLASK_APP=backend/app.py
    cd backend && python app.py
}

# ── Production Mode ─────────────────────────────────────────
run_prod() {
    setup_env
    info "Starting production server with Gunicorn..."
    export FLASK_ENV=production
    gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        "backend.app:create_app()"
}

# ── Docker Mode ─────────────────────────────────────────────
run_docker() {
    info "Building and starting Docker containers..."
    docker-compose up --build -d
    success "App running at http://localhost:5000"
    info "Logs: docker-compose logs -f"
    info "Stop: docker-compose down"
}

# ── Dataset Download ────────────────────────────────────────
download_data() {
    setup_env
    info "Downloading Food-101 dataset (this may take a while)..."
    python dataset/scripts/download_dataset.py --download --num_classes 101
    success "Dataset ready at dataset/food-101/"
}

# ── Sample Dataset ──────────────────────────────────────────
sample_data() {
    setup_env
    info "Creating sample dataset for testing..."
    python dataset/scripts/download_dataset.py --sample --num_classes 10
    success "Sample dataset ready at dataset/food-101/"
}

# ── Training ────────────────────────────────────────────────
run_training() {
    setup_env
    info "Starting model training..."
    info "Architecture: EfficientNet-B0 | Dataset: Food-101"
    python ml/training/train.py \
        --dataset_path dataset/food-101 \
        --output_dir models \
        --architecture efficientnet_b0 \
        --epochs 30 \
        --batch_size 64 \
        --learning_rate 0.001
    success "Training complete! Model saved to models/"
}

# ── Evaluation ──────────────────────────────────────────────
run_eval() {
    setup_env
    info "Evaluating model..."
    python ml/training/evaluate.py \
        --model_path models/food_classifier.pth \
        --dataset_path dataset/food-101/test \
        --verbose
}

# ── Tests ───────────────────────────────────────────────────
run_tests() {
    setup_env
    info "Running test suite..."
    python -m pytest tests/ -v
}

# ── Dispatch ────────────────────────────────────────────────
case "$MODE" in
    dev)      run_dev ;;
    prod)     run_prod ;;
    docker)   run_docker ;;
    data)     download_data ;;
    sample)   sample_data ;;
    train)    run_training ;;
    eval)     run_eval ;;
    test)     run_tests ;;
    *)
        echo "Usage: bash scripts/run.sh [dev|prod|docker|data|sample|train|eval|test]"
        echo ""
        echo "  dev     — Run Flask development server"
        echo "  prod    — Run with Gunicorn (production)"
        echo "  docker  — Run with Docker Compose"
        echo "  data    — Download Food-101 dataset"
        echo "  sample  — Create sample dataset for testing"
        echo "  train   — Train the ML model"
        echo "  eval    — Evaluate model performance"
        echo "  test    — Run test suite"
        exit 1 ;;
esac
