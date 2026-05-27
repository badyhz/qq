# Medium Operational Commit Isolation Checklist (T1278)

## Purpose

Define commit isolation rules for the 13 medium-risk untracked
operational scripts. Each script must be committed in isolation
with proper review artifacts.

## release_hold = HOLD

No commit of these scripts may proceed until hold is released.

## Checklist

### C1: Single-script commits

Each script must be committed individually. No bundling multiple
scripts into a single commit.

### C2: Commit message format

Commit messages must follow:

```
review: add medium-risk script <script_name> [T12XX]

- Dry-run default: YES
- Import boundary: PASS
- Deny-submit: PASS
- No credential: PASS
- No network: PASS
- release_hold: HOLD
```

### C3: Review artifact attachment

Each commit must include or reference:

- Script review evidence (from T1279 checklist)
- Dry-run execution log (local only)
- Import analysis results

### C4: No co-mingling

Script commits must NOT include changes to:

- Core modules (`core/`)
- Configuration files (`config.yaml`)
- Frozen files
- Other scripts in the batch

### C5: Commit ordering

Scripts must be committed in this order:

1. Verification scripts first (verify_*)
2. Replay scripts second (replay_*, run_replay_*)
3. Operational scripts third (run_*)
4. Safe-flatten scripts last (safe_flatten_*)

### C6: Pre-commit validation

Before each commit, run:

- Import boundary check
- Credential scan
- Network call detection
- Deny-submit verification

## Enforcement

- Pre-commit hooks must enforce C1-C4.
- Review checklist T1279 references this checklist.
