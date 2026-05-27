# Medium-Risk Verification Script Policy (T1173)

## Purpose

Define mandatory rules for medium-risk verification scripts.

## Rules

### R1: Read-only checks only

Verification scripts must only read state. They must not modify files,
database records, exchange positions, or any other mutable resource.

### R2: No mutation

No write operations. No file writes (except to `logs/` for output).
No API calls that change state (POST, PUT, DELETE). No subprocess
calls that mutate the filesystem.

### R3: No network calls unless explicitly dry-run

Verification scripts must not make network calls by default. If a
network call is required for verification, it must be gated behind
an explicit `--dry-run` or `--check` flag that the user must provide.

## Allowed Operations

- Read files in the repository
- Import and inspect model objects
- Validate data structures
- Check file existence and permissions
- Print reports to stdout / logs/

## Forbidden Operations

- Write to any file outside `logs/`
- Call exchange APIs (even read-only, unless explicitly flagged)
- Modify environment variables
- Spawn subprocesses that modify state
