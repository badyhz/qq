# Relay Git Write Safety Policy

Effective: 2026-06-15
Status: ACTIVE

## NO_AUTO_GIT_WRITE_RULE

1. **No `git commit`** unless the user explicitly authorizes commit in the current round.
2. **No `git tag`** unless the user explicitly authorizes tag creation in the current round.
3. **No `git push`** unless the user explicitly authorizes push in the current round.
4. **No `git push --tags`** unless the user explicitly authorizes tag push in the current round.
5. **Passing tests is not authorization.**
6. **A previous authorization is not reusable authorization.**

## Environment Gate

Automation entry points MUST check:

- `ALLOW_GIT_COMMIT` — must equal `YES` to permit `git commit`
- `ALLOW_GIT_TAG` — must equal `YES` to permit `git tag`
- `ALLOW_GIT_PUSH` — must equal `YES` to permit `git push`
- `ALLOW_GIT_DEPLOY` — must equal `YES` to permit deployment

Any unset or non-`YES` value means **DENIED**.

## Scope

This policy applies to:
- All relay / wrapper / prompt-driven automation
- All `cc-mimo-*` / `cc-deep-*` model route sessions
- All scripts in `scripts/` that invoke git
- All workflow templates in `automation/`

## Enforcement

- `core/relay_git_safety.py` — runtime guard module
- `scripts/check_relay_git_write_safety.py` — static scanner for dangerous patterns
- `tests/unit/test_relay_git_write_safety.py` — test coverage

## Violations

Any automated commit/tag/push without explicit per-round authorization is a policy violation.
Report must include: whether commit/tag/push occurred, and if so, whether it was authorized.
