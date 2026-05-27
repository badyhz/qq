# T1165 - Untracked Freeze Ledger: Forbidden Action Matrix

## Actions

| Action       | Description                                             |
|--------------|---------------------------------------------------------|
| AUTO_COMMIT  | Automatically stage and commit the file to git          |
| AUTO_WIRE    | Automatically add import/reference to the file          |
| AUTO_RUN     | Automatically execute or import the file                |
| DELETE       | Remove the file from disk without human approval        |
| MODIFY       | Alter file contents without human approval              |

## Matrix: risk_class x action -> forbidden

| Risk Class | AUTO_COMMIT | AUTO_WIRE | AUTO_RUN | DELETE  | MODIFY  |
|------------|-------------|-----------|----------|---------|---------|
| HIGH       | FORBIDDEN   | FORBIDDEN | FORBIDDEN| FORBIDDEN| FORBIDDEN|
| MEDIUM     | FORBIDDEN   | FORBIDDEN | FORBIDDEN| FORBIDDEN| FORBIDDEN|
| LOW        | FORBIDDEN   | FORBIDDEN | FORBIDDEN| FORBIDDEN| FORBIDDEN|

## Notes

- All five actions are FORBIDDEN for ALL risk classes by default.
- These actions may only be unblocked by an explicit human approval record
  that includes: operator identity, timestamp, file path, action, and reason.
- No automated system, agent, or script may perform these actions without
  a corresponding approval entry in the ledger.
- The FORBIDDEN status is absolute until overridden by human decision.
- Even LOW risk files cannot be auto-committed; the ledger enforces universal
  blocking of mutation actions.
