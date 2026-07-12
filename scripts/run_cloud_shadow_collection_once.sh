#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/opt/quant-shadow/qq"
LOG_DIR="$PROJECT_DIR/logs/cloud_shadow"
RUN_TS="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/shadow_collection_${RUN_TS}.log"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR"

{
  echo "=== Cloud Shadow Collection Start ==="
  date
  echo "project=$PROJECT_DIR"
  echo "user=$(whoami)"
  echo "pwd=$(pwd)"
  echo "git_head=$(git rev-parse HEAD)"

  . "$PROJECT_DIR/.venv/bin/activate"

  echo
  echo "=== Pre Status ==="
  python3 scripts/print_shadow_operator_status.py

  echo
  echo "=== Lifecycle ==="
  python3 scripts/run_shadow_trading_lifecycle.py --allow-public-http
  LIFECYCLE_EXIT=$?
  if [ $LIFECYCLE_EXIT -ne 0 ]; then
    echo "LIFECYCLE FAILED (exit=$LIFECYCLE_EXIT), aborting pipeline"
    exit 1
  fi

  echo
  echo "=== Update Only ==="
  python3 scripts/run_shadow_position_update_only.py --allow-public-http
  UPDATE_EXIT=$?
  if [ $UPDATE_EXIT -ne 0 ]; then
    echo "UPDATE-ONLY FAILED (exit=$UPDATE_EXIT), aborting pipeline"
    exit 1
  fi

  echo
  echo "=== Performance Scorecard ==="
  python3 scripts/run_paper_performance_scorecard.py
  SCORECARD_EXIT=$?
  if [ $SCORECARD_EXIT -ne 0 ]; then
    echo "SCORECARD FAILED (exit=$SCORECARD_EXIT), aborting pipeline"
    exit 1
  fi

  echo
  echo "=== Sample Gate ==="
  python3 scripts/run_sample_collection_gate.py
  GATE_EXIT=$?
  if [ $GATE_EXIT -ne 0 ]; then
    echo "GATE FAILED (exit=$GATE_EXIT), aborting pipeline"
    exit 1
  fi

  echo
  echo "=== Static Console ==="
  python3 scripts/generate_static_console.py
  CONSOLE_EXIT=$?
  if [ $CONSOLE_EXIT -ne 0 ]; then
    echo "CONSOLE FAILED (exit=$CONSOLE_EXIT), preserving last-good console"
  fi

  echo
  echo "=== Post Status ==="
  python3 scripts/print_shadow_operator_status.py

  echo
  echo "=== Cloud Shadow Collection End ==="
  date
} 2>&1 | tee "$LOG_FILE"
