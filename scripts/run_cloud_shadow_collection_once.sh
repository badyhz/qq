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
    local activate_closed_bar_cohort=0
    local activate_net_friction_cohort=0
    local friction_config="${NET_FRICTION_CONFIG:-}"
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --activate-closed-bar-cohort)
                activate_closed_bar_cohort=1
                shift
                ;;
            --activate-net-friction-cohort)
                activate_net_friction_cohort=1
                shift
                ;;
            --net-friction-config)
                if [ "$#" -lt 2 ]; then
                    echo "--net-friction-config requires a path" >&2
                    return 2
                fi
                friction_config="$2"
                shift 2
                ;;
            *)
                echo "Usage: $0 [--activate-closed-bar-cohort] [--activate-net-friction-cohort --net-friction-config PATH]" >&2
                return 2
                ;;
        esac
    done
    if [ "$activate_net_friction_cohort" -eq 1 ] && [ -z "$friction_config" ]; then
        echo "Net-friction activation requires explicit approved assumptions" >&2
        return 2
    fi

    mkdir -p "$LOG_DIR"
    cd "$PROJECT_DIR"

    {
        echo "=== Cloud Shadow Collection Start ==="
        date
        echo "project=$PROJECT_DIR"
        echo "user=$(whoami)"
        echo "pwd=$(pwd)"

        . "$PROJECT_DIR/.venv/bin/activate"

        RUN_COMMIT="$(git rev-parse HEAD)"
        if ! [[ "$RUN_COMMIT" =~ ^[0-9a-fA-F]{40}$ ]]; then
            echo "Executed Git commit is not a full hash"
            exit 1
        fi
        echo "git_head=$RUN_COMMIT"

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

        FRICTION_SCORECARD_ARGS=()
        FRICTION_ASSUMPTIONS_HASH=""
        if [ -n "$friction_config" ]; then
            if [ ! -f "$friction_config" ]; then
                echo "Net-friction assumptions file is unavailable: $friction_config"
                exit 1
            fi
            FRICTION_ASSUMPTIONS_HASH="$(python3 - "$friction_config" <<'PY'
import sys
from core.paper_trading.net_friction import assumptions_hash, load_assumptions, validate_assumptions
config = load_assumptions(sys.argv[1])
errors = validate_assumptions(config)
if errors:
    raise SystemExit("; ".join(errors))
print(assumptions_hash(config))
PY
)"
            if ! [[ "$FRICTION_ASSUMPTIONS_HASH" =~ ^[0-9a-f]{64}$ ]]; then
                echo "Net-friction assumptions validation FAILED"
                exit 1
            fi
            FRICTION_SCORECARD_ARGS=(--friction-config "$friction_config")
            echo "net_friction_assumptions_hash=$FRICTION_ASSUMPTIONS_HASH"
        else
            echo "net_friction_assumptions=UNCONFIGURED"
        fi

        echo
        echo "=== Pre Status ==="
        python3 scripts/print_shadow_operator_status.py

        echo
        run_step "Lifecycle" python3 scripts/run_shadow_trading_lifecycle.py \
            --allow-public-http \
            --date "$REPORT_DATE" \
            --run-id "$BATCH_RUN_ID" \
            --decision-cutoff "$BATCH_STARTED_AT" \
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
            --date "$REPORT_DATE" \
            "${FRICTION_SCORECARD_ARGS[@]}"

        echo
        run_step "Final Registry" python3 scripts/run_shadow_trading_lifecycle.py \
            --finalize-registry \
            --date "$REPORT_DATE" \
            --run-id "$BATCH_RUN_ID" \
            --batch-started-at "$BATCH_STARTED_AT"

        echo
        run_step "Gate" python3 scripts/run_sample_collection_gate.py \
            --date "$REPORT_DATE"

        if [ "$activate_closed_bar_cohort" -eq 1 ]; then
            ACTIVATION_TIMESTAMP="$(python3 -c '
from datetime import datetime, timezone
print(datetime.now(timezone.utc).isoformat(timespec="seconds"))
')"
            if [ -z "$ACTIVATION_TIMESTAMP" ]; then
                echo "Cohort activation timestamp generation FAILED"
                exit 1
            fi
            echo
            run_step "Closed-Bar Cohort Activation" \
                python3 scripts/run_paper_position_simulator.py \
                --output-dir "$PROJECT_DIR/reports/strategies" \
                --activate-closed-bar-cohort \
                --cohort-start-at "$ACTIVATION_TIMESTAMP" \
                --cohort-start-run-id "$BATCH_RUN_ID" \
                --cohort-start-commit "$RUN_COMMIT"

            echo
            run_step "Post-Activation Scorecard" \
                python3 scripts/run_paper_performance_scorecard.py \
                --date "$REPORT_DATE" \
                "${FRICTION_SCORECARD_ARGS[@]}"
        fi

        if [ "$activate_net_friction_cohort" -eq 1 ]; then
            NET_FRICTION_ACTIVATION_TIMESTAMP="$(python3 -c '
from datetime import datetime, timezone
print(datetime.now(timezone.utc).isoformat(timespec="seconds"))
')"
            echo
            run_step "Net-Friction Cohort Activation" \
                python3 scripts/run_paper_position_simulator.py \
                --output-dir "$PROJECT_DIR/reports/strategies" \
                --activate-net-friction-cohort \
                --net-friction-start-at "$NET_FRICTION_ACTIVATION_TIMESTAMP" \
                --net-friction-start-run-id "$BATCH_RUN_ID" \
                --net-friction-start-commit "$RUN_COMMIT" \
                --net-friction-assumptions-hash "$FRICTION_ASSUMPTIONS_HASH"

            echo
            run_step "Post-Net-Friction Scorecard" \
                python3 scripts/run_paper_performance_scorecard.py \
                --date "$REPORT_DATE" \
                "${FRICTION_SCORECARD_ARGS[@]}"
        fi

        echo
        echo "=== Static Console ==="
        if python3 scripts/generate_static_console.py \
            --server-commit "$RUN_COMMIT" \
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
