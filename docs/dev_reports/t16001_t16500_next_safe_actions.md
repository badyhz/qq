# T16001-T16500 Next Safe Actions

## Current State

Evidence checklist and manual approval forms have been generated. All items are PENDING. No approvals granted. No actions taken.

## Next Safe Actions (Human Required)

1. **Review evidence checklist** — open `backup_evidence_checklist.md`, review each file's requirements
2. **Collect hash evidence** — for each file, compute SHA256, record in evidence file
3. **Collect size evidence** — for each file, record exact byte size
4. **Confirm paths** — verify original paths match manifest
5. **Assign owners** — for each file, assign a human owner
6. **Review rollback plans** — verify rollback paths are feasible
7. **Complete approval forms** — fill in reviewer name, decision, signature
8. **Validate completed forms** — run validator on completed forms

## Still Forbidden

- No actual backup
- No actual archive
- No actual delete
- No actual move
- No actual copy
- No live/testnet/runtime activation
- No automated approval

## Recommended Next Phase

T16501-T17000: Offline Backup Approval Dry-Run Validator / Completed Form Simulation

This phase will:
- Accept completed human approval forms
- Validate completed forms against evidence checklist
- Simulate what would happen if approval were acted upon
- Still no actual backup/copy/move/delete
