# Frozen Inventory Backup Before Delete Policy

## Policy

No frozen file may be deleted without:
1. A verified backup copy
2. Explicit human approval
3. Integrity verification of the backup

## Backup Requirements

- Backup must be in a separate location from the original
- Backup SHA256 must match original
- Backup must be verified readable
- Backup location must be documented

## Delete Workflow

1. Create backup
2. Verify backup integrity (SHA256 match)
3. Verify backup is readable
4. Document backup location
5. Request human approval
6. Human approves
7. Delete original
8. Verify deletion
9. Document deletion

## Rollback

If deletion was incorrect:
1. Restore from verified backup
2. Verify restored file matches original SHA256
3. Document restoration

## Safety Boundary

- No deletion without backup
- No deletion without human approval
- No deletion without integrity verification
- release_hold = HOLD
- Advisory only
