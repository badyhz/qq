# Frozen Archive Simulation

## Overview

The archive simulation models what would happen if archive/delete/rewrite actions were approved. This is simulation only — no actual file operations occur.

## Safety Boundary

- `would_copy`: **false** for all items
- `would_move`: **false** for all items
- `would_delete`: **false** for all items
- `would_modify`: **false** for all items
- `simulation_only`: **true** for all items
- `human_approval_required`: **true** for all items
- `release_hold`: **HOLD**

## Valid Final Statuses

| Status | Meaning |
|--------|---------|
| SIMULATED_READY_FOR_HUMAN_REVIEW | Ready for human to review |
| BLOCKED_PENDING_BACKUP | Blocked until backup is done |
| BLOCKED_PENDING_HUMAN_APPROVAL | Blocked until human approves |
| BLOCKED_UNKNOWN_RISK | Unknown risk, needs review |
| KEEP_FROZEN_NO_ACTION | No action needed |
| REVIEW_REQUIRED | More review needed |

## Forbidden Statuses

ARCHIVED, DELETED, MOVED, EXECUTED, IMPORTED, ACTIVATED — none of these may appear.

## CLI

```bash
PYTHONPATH=. python3 scripts/simulate_frozen_archive_plan.py \
  --backup-manifest-dir /tmp/frozen_backup_manifest \
  --output-dir /tmp/frozen_archive_simulation \
  --strict \
  --release-hold HOLD
```

## Outputs

- `/tmp/frozen_archive_simulation/archive_simulation.json`
- `/tmp/frozen_archive_simulation/archive_simulation.md`
- `/tmp/frozen_archive_simulation/archive_simulation_manifest.json`

## No Actual Operations

This module does NOT:
- Archive files
- Delete files
- Move files
- Copy files
- Modify files
