# Medium Operational Artifact Write Policy (T1273)

## Purpose

Define file output rules for the 13 medium-risk untracked
operational scripts. Scripts may generate artifacts but must
not modify frozen or tracked files.

## release_hold = HOLD

No artifact generated under this policy may be promoted to
production paths until the hold is released.

## Policy

### P1: Allowed write destinations

Scripts may write ONLY to:

- `logs/` - execution logs
- `artifacts/` - generated reports, CSVs, JSONs
- `tmp/` - temporary scratch files
- `evidence/` - review evidence packets

### P2: Forbidden write destinations

Scripts must NOT write to:

- `core/` - frozen module directory
- `utils/` - frozen utility directory
- `config.yaml` - system configuration
- `.env` or any credential file
- Any file tracked by git in `main` branch

### P3: Artifact naming

All artifacts must include:

- Script name prefix
- ISO date suffix (YYYY-MM-DD)
- Appropriate extension (.json, .csv, .log)

Example: `run_shadow_scan_2026-05-27.json`

### P4: No symlink creation

Scripts must NOT create symlinks that could redirect writes
to forbidden destinations.

### P5: Artifact size limit

Single artifact files must not exceed 50MB. Scripts must
implement chunking if output may exceed this limit.

## Enforcement

- Review checklist T1279 includes artifact policy checks.
- Post-run audit must verify no forbidden writes occurred.
