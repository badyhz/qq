# Verification Script No Side Effect Policy

**Task ID:** T1285
**release_hold:** HOLD
**Status:** Active

## Policy

Verification scripts must produce zero side effects on the host system.

## Prohibited Side Effects

| Category | Examples |
|----------|----------|
| File writes | Creating/modifying files outside tmp |
| Network calls | HTTP requests, WebSocket connections |
| Process spawn | subprocess.run, os.system |
| Environment mutation | os.environ modification without restore |
| State file mutation | Modifying config.yaml, acceptance.json |
| Log pollution | Writing to production log paths |

## Allowed Side Effects

- Writing to `/tmp/verify_*` prefixed files (auto-cleaned)
- Stdout/stderr output for reporting
- In-memory state changes within the script process

## Verification Methods

1. **Pre/post diff** — Run script, diff workspace, confirm zero changes
2. **Strace/dtrace** — Attach to script process, flag write/connect syscalls
3. **Sandbox run** — Run in container with read-only filesystem

## Review Gate

- Any prohibited side effect = REJECT
- Script must pass pre/post diff with zero workspace changes
- release_hold remains HOLD until side-effect-free proof is documented
