# Frozen Backup Manifest

## Overview

The frozen backup manifest records what must be backed up before any archive/delete/rewrite action on frozen files. This is simulation only — no actual backup copies are created.

## Safety Boundary

- `backup_allowed_now`: **false** for all items
- `required_human_approval`: **true** for all items
- `no_touch_required`: **true** for all items
- `backup_simulation_only`: **true** for all items
- `advisory_only`: **true** for all items
- `release_hold`: **HOLD**

## Backup Classes

| Class | Meaning | Backup Required |
|-------|---------|----------------|
| REQUIRED_BEFORE_ARCHIVE | File is candidate for archive | Yes |
| REQUIRED_BEFORE_DELETE | File is candidate for delete | Yes |
| REQUIRED_BEFORE_REWRITE | File is candidate for rewrite | Yes |
| OPTIONAL_FOR_KEEP_FROZEN | File stays frozen | Optional |
| REVIEW_REQUIRED | Needs more human review | TBD |
| UNKNOWN | Unknown risk | TBD |

## What This Answers

- If a human later approves archive/delete, what exactly must be backed up?
- What hashes must be recorded before any destructive action?
- What manifest should exist before any destructive action?

## CLI

```bash
PYTHONPATH=. python3 scripts/build_frozen_backup_manifest.py \
  --decision-prep-dir /tmp/frozen_archive_delete_decision_prep \
  --inventory-dir /tmp/frozen_inventory_review \
  --output-dir /tmp/frozen_backup_manifest \
  --strict \
  --release-hold HOLD
```

## Outputs

- `/tmp/frozen_backup_manifest/backup_manifest.json`
- `/tmp/frozen_backup_manifest/backup_manifest.md`
- `/tmp/frozen_backup_manifest/backup_manifest_manifest.json`

## No Actual Operations

This module does NOT:
- Create actual backup copies
- Move files
- Delete files
- Modify files
- Execute files
