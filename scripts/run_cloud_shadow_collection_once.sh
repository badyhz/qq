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
    if "$@"; then
        return 0
    else
        local rc=$?
        echo "${name} FAILED (exit=${rc})"
        return "${rc}"
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
  if python3 scripts/generate_static_console.py --server-commit "$SERVER_COMMIT"; then
    CONSOLE_RC=0
  else
    CONSOLE_RC=$?
    echo "CONSOLE FAILED (exit=${CONSOLE_RC}), LAST-GOOD PRESERVED"
  fi

  echo
  echo "=== Post Status ==="
  python3 scripts/print_shadow_operator_status.py

  echo
  echo "=== Cloud Shadow Collection End ==="
  date

  if [ "$CONSOLE_RC" -ne 0 ]; then
    exit "$CONSOLE_RC"
  fi
} 2>&1 | tee "$LOG_FILE"
