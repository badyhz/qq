# Frozen File Human Review Queue

## What This Stage Does

Builds a prioritized human review queue from the frozen inventory decision matrix. Each frozen file is classified by priority (P0-P3, UNKNOWN) with required questions, evidence, and safe possible decisions.

## What It Does NOT Do

- Does NOT execute, import, stage, move, delete, or rename any frozen file
- Does NOT make any automated decisions
- Does NOT activate live/testnet/runtime
- Does NOT place, cancel, or flatten orders

## How to Regenerate Queue

```bash
# Prerequisites: decision matrix must exist
PYTHONPATH=. python3 scripts/build_frozen_inventory_report.py \
  --output-dir /tmp/frozen_inventory_review \
  --release-hold HOLD --strict

PYTHONPATH=. python3 scripts/build_frozen_inventory_decision_matrix.py \
  --inventory-dir /tmp/frozen_inventory_review \
  --output-dir /tmp/frozen_inventory_decision_matrix \
  --strict --release-hold HOLD

# Build queue
PYTHONPATH=. python3 scripts/build_frozen_human_review_queue.py \
  --decision-matrix-dir /tmp/frozen_inventory_decision_matrix \
  --output-dir /tmp/frozen_human_review_queue \
  --strict --release-hold HOLD
```

## How to Interpret Priorities

| Priority | Keywords | Reviewer |
|----------|----------|----------|
| P0_CRITICAL_REVIEW | submit, cancel, flatten, live, runtime, binance, fapi | senior_operator |
| P1_HIGH_REVIEW | testnet, order, positionRisk, exchange | operator |
| P2_STANDARD_REVIEW | shadow, observation, verify | reviewer |
| P3_LOW_REVIEW | other | reviewer |
| UNKNOWN_REVIEW | no keywords, UNKNOWN category | operator |

## Possible Decisions (Safe Only)

- KEEP_FROZEN
- ARCHIVE_AFTER_BACKUP
- REWRITE_OFFLINE_ONLY
- DELETE_AFTER_BACKUP
- NEEDS_MORE_REVIEW

## Forbidden Decisions

EXECUTE, IMPORT, ACTIVATE_LIVE, ACTIVATE_TESTNET, ENABLE_RUNTIME, ENABLE_PLANNER, SUBMIT_ORDER, CANCEL_ORDER, FLATTEN_POSITION, APPROVE_WITHOUT_BACKUP

## No-Touch Statement

All frozen files require explicit human review and approval before any action. No file may be executed, imported, staged, moved, deleted, or renamed without approval.

## Safety

- release_hold: **HOLD**
- advisory_only: **true**
- human_review_required: **true**
- No activation permitted.
