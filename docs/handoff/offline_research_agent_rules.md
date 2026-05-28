# Offline Research Agent Rules

## Hard Constraints

1. Offline only — no network access
2. No Binance — no exchange interaction
3. No live trading — no real orders
4. No testnet submit — no test orders
5. release_hold = HOLD — never release without human approval
6. Advisory only — research output is advisory, not executable
7. Human review required — no auto-promotion

## File Safety

1. Never execute frozen files
2. Never import frozen files
3. Never stage frozen files
4. Never modify pre-existing untracked files
5. Never delete pre-existing untracked files
6. Never rename pre-existing untracked files
7. Use explicit git add only — never git add .

## Development Rules

1. Read PROJECT_STATE.md before changes
2. Read TASKS.md before changes
3. Test in dry-run mode
4. Update control files after changes
5. Document all changes

## Output Rules

1. Research output is advisory only
2. No recommendation to activate live/testnet
3. No recommendation to execute frozen files
4. Safety boundary in all outputs
5. release_hold in all manifests
