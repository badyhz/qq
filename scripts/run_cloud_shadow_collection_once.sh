#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/quant-shadow/qq}"
LOG_DIR="$PROJECT_DIR/logs/cloud_shadow"
RUN_TS="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/shadow_collection_${RUN_TS}.log"

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

main() {
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

        read -r BATCH_RUN_ID BATCH_STARTED_AT REPORT_DATE < <(
            python3 -c '
from core.paper_trading.shadow_run_registry import build_pipeline_context
context = build_pipeline_context()
print(context["run_id"], context["started_at"], context["report_date"])
'
        )
        if [ -z "$BATCH_RUN_ID" ] || [ -z "$BATCH_STARTED_AT" ] || [ -z "$REPORT_DATE" ]; then
            echo "Batch identity generation FAILED"
            exit 1
        fi
        echo "batch_run_id=$BATCH_RUN_ID"
        echo "batch_started_at=$BATCH_STARTED_AT"
        echo "report_date=$REPORT_DATE"

        echo
        echo "=== Pre Status ==="
        python3 scripts/print_shadow_operator_status.py

        echo
        run_step "Lifecycle" python3 scripts/run_shadow_trading_lifecycle.py \
            --allow-public-http \
            --date "$REPORT_DATE" \
            --run-id "$BATCH_RUN_ID" \
            --defer-position-update \
            --defer-scorecard \
            --defer-registry

        echo
        run_step "Update-Only" python3 scripts/run_shadow_position_update_only.py \
            --allow-public-http \
            --date "$REPORT_DATE" \
            --run-id "$BATCH_RUN_ID" \
            --defer-scorecard \
            --defer-gate \
            --defer-registry

        echo
        run_step "Scorecard" python3 scripts/run_paper_performance_scorecard.py \
            --date "$REPORT_DATE"

        echo
        run_step "Final Registry" python3 scripts/run_shadow_trading_lifecycle.py \
            --finalize-registry \
            --date "$REPORT_DATE" \
            --run-id "$BATCH_RUN_ID" \
            --batch-started-at "$BATCH_STARTED_AT"

        echo
        run_step "Gate" python3 scripts/run_sample_collection_gate.py \
            --date "$REPORT_DATE"

        echo
        echo "=== Static Console ==="
        SERVER_COMMIT="$(git rev-parse HEAD)"
        if python3 scripts/generate_static_console.py \
            --server-commit "$SERVER_COMMIT" \
            --report-date "$REPORT_DATE"; then
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
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
