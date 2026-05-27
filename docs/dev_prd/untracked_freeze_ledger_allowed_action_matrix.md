# T1164 - Untracked Freeze Ledger: Allowed Action Matrix

## Actions

| Action    | Description                                        |
|-----------|----------------------------------------------------|
| INSPECT   | Read file contents, compute hash, scan references  |
| CLASSIFY  | Assign state and risk class in ledger              |
| LOG       | Record observation in ledger without state change   |
| REPORT    | Generate summary or alert about file status         |

## Matrix: risk_class x action -> allowed/denied

| Risk Class | INSPECT | CLASSIFY | LOG  | REPORT |
|------------|---------|----------|------|--------|
| HIGH       | ALLOWED | ALLOWED  | ALLOWED | ALLOWED |
| MEDIUM     | ALLOWED | ALLOWED  | ALLOWED | ALLOWED |
| LOW        | ALLOWED | ALLOWED  | ALLOWED | ALLOWED |

## Notes

- All four actions are read-only or metadata-only. They do not modify the file.
- INSPECT does not execute the file; it reads contents and computes hashes.
- CLASSIFY updates ledger metadata only; it does not touch the file on disk.
- LOG appends to the ledger; it is append-only.
- REPORT generates output for human consumption; it does not change state.
- These actions are permitted for ALL risk classes without restriction.
