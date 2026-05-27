# Medium Operational No-Credential Policy (T1276)

## Purpose

Define the prohibition on credential usage for the 13 medium-risk
untracked operational scripts. Scripts must not reference, embed,
or access any secrets or API keys.

## release_hold = HOLD

Credential restrictions hold regardless of hold state.

## Policy

### P1: No hardcoded secrets

Scripts must NOT contain:

- API keys or secrets as string literals
- Passwords or passphrases
- Private keys or seed phrases
- Bearer tokens or JWTs

### P2: No credential file reads

Scripts must NOT read from:

- `.env` files
- `credentials.json`
- `secrets.yaml`
- Any file containing exchange credentials

### P3: No credential environment access

Scripts must NOT read environment variables that contain:

- API keys (`*_API_KEY`, `*_SECRET`)
- Tokens (`*_TOKEN`, `*_BEARER`)
- Passwords (`*_PASSWORD`, `*_PASS`)

Exception: `DRY_RUN=true` and similar mode flags are permitted.

### P4: No credential transmission

Scripts must NOT transmit credentials to:

- Log files
- Artifact files
- stdout/stderr
- Network endpoints

### P5: Placeholder convention

If a script needs to reference credential structures for
documentation purposes, it must use:

- `<REDACTED>` as placeholder
- `PLACEHOLDER_API_KEY` pattern
- Comments explaining the structure without values

## Enforcement

- Pre-commit hook: scan for credential patterns.
- Review checklist T1279 includes credential checks.
- Any violation is a BLOCKER for promotion.
