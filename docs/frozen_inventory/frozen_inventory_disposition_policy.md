# Frozen Inventory Disposition Policy

## Policy Statement

All frozen inventory files require human review before any disposition action.
No automated system may approve, execute, import, or stage any frozen file.

## Disposition Workflow

1. **Audit** — Scan files, detect risk keywords, classify categories.
2. **Decision Matrix** — Map each file to a disposition category.
3. **Human Review** — Human reviews matrix and approves/rejects dispositions.
4. **Archive Plan** — If approved, create a no-touch archive plan.
5. **Execution** — Only after explicit human approval per file.

## Risk Scoring

| Score Range | Interpretation |
|-------------|----------------|
| 0 | No risk detected |
| 1-4 | Low risk |
| 5-14 | Moderate risk |
| 15-29 | High risk |
| 30+ | Critical risk |

## Category-to-Disposition Mapping

| Audit Category | Default Disposition |
|---------------|-------------------|
| LIVE | NEEDS_HUMAN_REVIEW |
| SUBMIT | CANDIDATE_FOR_ARCHIVE |
| FLATTEN | CANDIDATE_FOR_REWRITE |
| CANCEL | CANDIDATE_FOR_REWRITE |
| TESTNET | NEEDS_HUMAN_REVIEW |
| SHADOW | NEEDS_HUMAN_REVIEW |
| OBSERVATION | NEEDS_HUMAN_REVIEW |
| RUNTIME | NEEDS_HUMAN_REVIEW |
| UNKNOWN | NEEDS_HUMAN_REVIEW |

## Forbidden Outcomes

- No file may be auto-promoted
- No file may be marked SAFE_TO_EXECUTE
- No file may be marked SAFE_TO_IMPORT
- release_hold must remain HOLD until explicit human release

## Human Action Requirements

- KEEP_FROZEN: No action required
- NEEDS_HUMAN_REVIEW: Inspect file, decide disposition
- CANDIDATE_FOR_ARCHIVE: Verify no live dependencies, approve archive
- CANDIDATE_FOR_REWRITE: Approve rewrite scope, review output
- CANDIDATE_FOR_DELETION_AFTER_BACKUP: Verify backup, approve deletion
- UNKNOWN: Full inspection required
