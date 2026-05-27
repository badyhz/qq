# Medium-Risk Promotion to Commit Checklist (T1179)

## Purpose

Define the checklist that must be completed before a medium-risk
script can be promoted to a git commit.

## Checklist

### C1: Dry-run verified

- [ ] Script runs successfully in dry-run mode
- [ ] No real orders submitted
- [ ] No real network calls to exchange endpoints
- [ ] All actions logged to stdout and/or logs/

### C2: Imports clean

- [ ] No direct imports from HIGH-risk modules
- [ ] Abstraction layer used where needed
- [ ] Import block at top of file documents risk classification

### C3: No secrets

- [ ] No hardcoded API keys, passwords, or tokens
- [ ] No secrets in log output
- [ ] Environment variables used for credentials

### C4: No live paths

- [ ] No code path that can reach live mode without explicit flag
- [ ] Default mode is dry-run
- [ ] Live mode prints warning before executing

### C5: Human approved

- [ ] Human has reviewed the script
- [ ] Human has approved the commit
- [ ] Commit message includes explicit file list

## Verdict

All items must be checked. Any unchecked item results in BLOCKED status.
