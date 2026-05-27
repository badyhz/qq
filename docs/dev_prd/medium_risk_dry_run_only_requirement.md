# Medium-Risk Dry-Run-Only Requirement (T1174)

## Purpose

Enforce that all medium-risk scripts default to dry-run and require
explicit human action to escalate to live or testnet modes.

## Rules

### R1: Default mode must be dry-run

Every medium-risk script must use `dry-run` as its default execution
mode. This means:

- No real orders submitted
- No real network calls to exchange endpoints
- All actions logged but not executed
- Output shows what *would* happen

### R2: Live mode requires explicit human flag

To run in live mode, the user must explicitly provide a flag such as:

```
--mode=live
```

The script must validate that this flag is present and must refuse to
run in live mode without it. Scripts must print a clear warning before
any live action.

### R3: Testnet mode requires approval

Testnet mode sits between dry-run and live. To run in testnet mode:

- The user must provide `--mode=testnet`
- The script must check for a human approval artifact or confirm
  interactively
- All testnet actions must still be logged

## Mode Hierarchy

| Mode        | Flag              | Requirements             |
|-------------|-------------------|--------------------------|
| dry-run     | (default)         | None                     |
| testnet     | `--mode=testnet`  | Human approval           |
| live        | `--mode=live`     | Explicit flag + warning  |

## Enforcement

- Scripts that lack a mode flag must default to dry-run.
- The promotion checklist (T1179) verifies this behavior.
