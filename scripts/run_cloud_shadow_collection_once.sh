#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/opt/quant-shadow/qq"
LOG_DIR="$PROJECT_DIR/logs/cloud_shadow"
RUN_TS="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/shadow_collection_${RUN_TS}.log"

mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR"

run_step() {
    local name="$1"
    shift
    echo "=== ${name} ==="
    if ! "$@"; then
        echo "${name} FAILED (exit=$?)"
        return 1
    fi
}

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
  run_step "Lifecycle" python3 scripts/run_shadow_trading_lifecycle.py --allow-public-http

  echo
  run_step "Update-Only" python3 scripts/run_shadow_position_update_only.py --allow-public-http

  echo
  run_step "Scorecard" python3 scripts/run_paper_performance_scorecard.py

  echo
  run_step "Gate" python3 scripts/run_sample_collection_gate.py

  echo
  echo "=== Static Console ==="
  SERVER_COMMIT="$(git rev-parse HEAD)"
  if ! python3 scripts/generate_static_console.py --server-commit "$SERVER_COMMIT"; then
    echo "CONSOLE FAILED, LAST-GOOD PRESERVED"
    CONSOLE_FAILED=1
  else
    CONSOLE_FAILED=0
  fi

  echo
  echo "=== Post Status ==="
  python3 scripts/print_shadow_operator_status.py

  echo
  echo "=== Cloud Shadow Collection End ==="
  date

  if [ "$CONSOLE_FAILED" -ne 0 ]; then
    echo "Pipeline completed with console failure"
    exit 1
  fi
} 2>&1 | tee "$LOG_FILE"
