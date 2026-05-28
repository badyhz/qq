# Frozen Inventory Human Decision Matrix

## Purpose

Turn frozen inventory audit records into a human disposition matrix for informed decision-making.

## Decision Categories

| Category | Meaning |
|----------|---------|
| KEEP_FROZEN | No action needed. Remain frozen. |
| NEEDS_HUMAN_REVIEW | Human must inspect and decide. |
| CANDIDATE_FOR_ARCHIVE | Can be archived after human approval. |
| CANDIDATE_FOR_REWRITE | Must be rewritten before any use. |
| CANDIDATE_FOR_DELETION_AFTER_BACKUP | Can be deleted after backup verification. |
| UNKNOWN | Cannot determine. Human review required. |

## Classification Rules

1. Any path containing `live`, `submit`, `order`, `cancel`, `flatten`, `testnet`, `runtime`, `fapi`, `binance` gets `NEEDS_HUMAN_REVIEW` unless a stronger rule applies.
2. Any path with `flatten`/`cancel`/`submit` gets `CANDIDATE_FOR_REWRITE` or `CANDIDATE_FOR_ARCHIVE`, never safe.
3. `UNKNOWN` category always maps to `NEEDS_HUMAN_REVIEW`.
4. No file may be marked `APPROVED`, `SAFE_TO_EXECUTE`, or `SAFE_TO_IMPORT`.

## Output Fields

Each entry contains:
- `path` — file path
- `exists` — whether file exists
- `status` — git status
- `category` — audit category
- `risk_keywords` — detected risk keywords
- `risk_score` — numeric risk score
- `disposition` — decision category
- `disposition_reason` — why this disposition
- `required_human_action` — what human must do
- `allowed_agent_action` — always "none"
- `forbidden_agent_action` — execute, import, stage, modify, delete, rename
- `no_execution` — always true
- `no_import` — always true
- `no_stage` — always true
- `release_hold` — always "HOLD"
- `advisory_only` — always true
- `human_review_required` — always true

## Safety Boundary

- No file marked APPROVED
- No file marked SAFE_TO_EXECUTE
- No file marked SAFE_TO_IMPORT
- release_hold = HOLD
- Advisory only. Human review required.
- No execution. No import. No staging.

## CLI

```bash
python3 scripts/build_frozen_inventory_decision_matrix.py \
    --inventory-dir /tmp/frozen_inventory_review \
    --output-dir /tmp/frozen_inventory_decision_matrix \
    --strict \
    --release-hold HOLD
```

## Outputs

- `decision_matrix.json` — full matrix
- `decision_matrix.md` — human-readable summary
- `decision_matrix_manifest.json` — manifest with safety flags
