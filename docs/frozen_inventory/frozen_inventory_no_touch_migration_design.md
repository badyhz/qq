# Frozen Inventory No-Touch Migration Design

## Design Principles

1. **No-touch** — No file is moved, deleted, renamed, or modified by the plan.
2. **Advisory only** — The plan proposes; humans dispose.
3. **Human approval required** — Every risky action requires explicit human approval.
4. **Backup before action** — Any destructive action requires verified backup first.
5. **Rollback ready** — Every proposed action includes a rollback note.

## Migration Workflow (Future)

1. Human reviews decision matrix
2. Human reviews archive plan
3. Human approves specific file actions
4. Backup created and verified
5. Action executed under human supervision
6. Rollback available if needed

## Preconditions Per Action

### Archive
- Human approval
- No live dependencies
- Backup created

### Rewrite
- Human approval of scope
- Original backed up
- Rewritten version reviewed

### Delete
- Backup verified
- Human approval
- Integrity check passed

## Forbidden Until Approved

- execute
- import
- stage
- move
- delete
- rename
- modify
- overwrite

## Safety Boundary

- release_hold = HOLD
- No-touch confirmed
- Advisory only
- Human review required
