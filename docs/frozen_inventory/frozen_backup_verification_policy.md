# Frozen Backup Verification Policy

## Overview

The backup verification module checks that backup manifest and archive simulation data comply with all safety invariants before any human review or action.

## Verification Checks

| Check | Description |
|-------|-------------|
| release_hold_is_HOLD | Input release_hold must be HOLD |
| advisory_only | All items must be advisory only |
| simulation_only | All items must be simulation only |
| human_review_required | All items require human review |
| no_forbidden_statuses_in_backup | No BACKUP_DONE, SAFE_TO_DELETE, etc. |
| no_forbidden_statuses_in_simulation | No ARCHIVED, DELETED, MOVED, etc. |
| all_proposed_paths_hypothetical | Paths must start with archive_simulation/ |
| all_would_flags_false | would_copy/move/delete/modify all false |
| simulation_human_approval_required | All simulation items require approval |
| backup_allowed_now_false | backup_allowed_now must be false |
| output_hash_stable | Deterministic output hash |

## CLI

```bash
PYTHONPATH=. python3 scripts/verify_frozen_backup_manifest.py \
  --backup-manifest-dir /tmp/frozen_backup_manifest \
  --archive-simulation-dir /tmp/frozen_archive_simulation \
  --output-dir /tmp/frozen_backup_verification \
  --strict \
  --release-hold HOLD
```

## Outputs

- `/tmp/frozen_backup_verification/backup_verification.json`
- `/tmp/frozen_backup_verification/backup_verification.md`
- `/tmp/frozen_backup_verification/backup_verification_manifest.json`

## Failure Modes

Verification fails if:
- Any forbidden status appears (BACKUP_DONE, ARCHIVED, DELETED, etc.)
- Any proposed path is not hypothetical
- Any would_* flag is true
- release_hold is not HOLD
- Human review not required
