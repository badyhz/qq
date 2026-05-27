# Medium Operational Review Checklist (T1279)

## Purpose

Define the promotion gate checklist for the 13 medium-risk untracked
operational scripts. All items must pass before any script can be
committed or promoted.

## release_hold = HOLD

All scripts remain on hold. Checklist completion does not release
the hold; that requires explicit human decision.

## Checklist

### Category A: Safety (BLOCKER if failed)

| ID   | Check                              | Policy Ref | Pass |
|------|------------------------------------|------------|------|
| A1   | Dry-run default confirmed          | T1272      | [ ]  |
| A2   | No live order submission           | T1275      | [ ]  |
| A3   | No hardcoded credentials           | T1276      | [ ]  |
| A4   | No live network calls              | T1277      | [ ]  |
| A5   | No eval/exec on untrusted input    | T1272      | [ ]  |

### Category B: Structure (WARNING if failed)

| ID   | Check                              | Policy Ref | Pass |
|------|------------------------------------|------------|------|
| B1   | Import boundaries respected        | T1274      | [ ]  |
| B2   | Artifact writes to allowed paths   | T1273      | [ ]  |
| B3   | Command logging present            | T1272      | [ ]  |
| B4   | No shell=True in subprocess        | T1272      | [ ]  |
| B5   | Kill switch implemented            | T1275      | [ ]  |

### Category C: Process (REQUIRED for promotion)

| ID   | Check                              | Policy Ref | Pass |
|------|------------------------------------|------------|------|
| C1   | Commit isolation verified          | T1278      | [ ]  |
| C2   | Review artifact attached           | T1278      | [ ]  |
| C3   | Dry-run execution log captured     | T1272      | [ ]  |
| C4   | release_hold = HOLD confirmed      | T1271      | [ ]  |

## Scoring

- All Category A items must pass (BLOCKER).
- Category B items generate warnings; >3 warnings = BLOCKER.
- All Category C items required for promotion.

## Sign-off

- Reviewer: _______________
- Date: _______________
- Verdict: PASS / FAIL / HOLD
