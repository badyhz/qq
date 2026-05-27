# Medium-Risk Artifact Policy (T1177)

## Purpose

Control where medium-risk scripts write output files.

## Rules

### R1: Output files must be in logs/ or tmp/

All artifact output from medium-risk scripts must go to:

- `logs/` - for audit-trail artifacts (reports, logs, verdicts)
- `tmp/` - for temporary artifacts (intermediate files, caches)

### R2: No writes to core/

Medium-risk scripts must never write files to the `core/` directory.
Core modules are code, not runtime output.

### R3: No writes to config

Medium-risk scripts must never modify `config.yaml`, `acceptance.json`,
`feature_list.json`, or any other configuration file.

### R4: Human review for new artifacts

If a medium-risk script introduces a new artifact type (a new file
pattern not previously seen), it requires human review before the
script can be promoted to commit.

## Allowed Write Destinations

| Directory | Purpose              | Review Required |
|-----------|----------------------|-----------------|
| `logs/`   | Reports, audit trail | No              |
| `tmp/`    | Temporary files      | No              |
| `core/`   | (FORBIDDEN)          | N/A             |
| `config*` | (FORBIDDEN)          | N/A             |
