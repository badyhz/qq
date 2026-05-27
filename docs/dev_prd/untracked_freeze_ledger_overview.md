# T1161 - Untracked Freeze Ledger Overview

## Purpose

The Untracked Freeze Ledger is a safety mechanism that inventories all untracked files
in the repository, classifies them by risk, and enforces a freeze policy that prevents
unsafe automated actions (auto-commit, auto-wire, auto-run, delete, modify) until each
file has been explicitly reviewed and approved by a human operator.

## Scope

- Covers every file reported by `git status` as untracked (`??` prefix).
- Does NOT modify any existing tracked file.
- Does NOT interact with live trading, exchange APIs, secrets, or runtime planners.
- Read-only by default; all mutations require human approval.

## File States

| State        | Meaning                                          |
|--------------|--------------------------------------------------|
| NEW          | First time observed, no prior classification     |
| STALE        | Unmodified for N days since last observed change |
| FROZEN       | Explicitly frozen by operator decision           |
| DUPLICATE    | Content-identical to another tracked/untracked file |
| ORPHAN       | Referenced by no module, no import, no config    |
| QUARANTINED  | Flagged for removal or special handling          |

## Risk Classes

| Class  | Criteria                                              |
|--------|-------------------------------------------------------|
| HIGH   | Could affect trading, secrets, or runtime if acted on |
| MEDIUM | Infrastructure or config file with indirect impact    |
| LOW    | Documentation, test fixtures, inert data              |

## Enforcement

1. All untracked files are logged to the ledger on each scan.
2. Each file is assigned a state and risk class.
3. Allowed actions: INSPECT, CLASSIFY, LOG, REPORT.
4. Forbidden actions: AUTO_COMMIT, AUTO_WIRE, AUTO_RUN, DELETE, MODIFY.
5. Forbidden actions are blocked until human review produces an explicit approval record.

## Safety Statement

This ledger exists to prevent untracked files from silently entering the codebase,
affecting trading logic, or being lost. No file transitions past QUARANTINED without
a recorded human decision. The system defaults to blocking, never permitting.
