# Phase2 Exit Criteria

## 1. Phase2 Definition

Phase2 covers guard integration into non-frozen, SAFE_READONLY scripts. Each script receives `assert_dry_run_required` at CLI `main()` entry.

Scope: all scripts classified `SAFE_READONLY` in `execution_guard_safe_taxonomy.md`.

## 2. Exit Criteria

### Minimum Requirements

| Criterion | Target | Current |
|---|---|---|
| SAFE_READONLY_CANDIDATE scripts guarded | 41/41 | 30/41 |
| Guard tests pass | 0 failures | — |
| Regression tests pass | 124/124 | — |
| Frozen file modifications | 0 | 0 |
| Runtime/planner integration | none | none |
| Documentation complete | all sections | in progress |

### Test Requirements

Each guarded script must pass 6 guard tests:

1. `import_safe` — script imports without side effects
2. `no_high_risk_imports` — no frozen module imports
3. `default_dry_run` — defaults to dry-run mode
4. `dry_run_pass` — executes cleanly in dry-run
5. `live_block` — blocks live order submission
6. `bogus_block` — blocks BogusOrderConfig payloads

Regression suite: 124 tests (execution_guards + schema + contract).

Skip policy: documented, non-blocking, tracked in `execution_guard_phase2_validation_plan.md`.

### Documentation Requirements

- [ ] runbook current (`execution_guard_phase2_runbook.md`)
- [ ] integration matrix current (`execution_guard_integration_matrix.md`)
- [ ] coverage dashboard current (`execution_guard_coverage_dashboard.md`)
- [ ] taxonomy complete (`execution_guard_safe_taxonomy.md`)
- [ ] backlog plan current (`execution_guard_safe_backlog_plan.md`)
- [ ] skipped test governance documented

### Rollback Requirements

- Each batch independently reversible via `git revert`
- Frozen boundary verified before/after each batch
- `git diff -- docs/` clean per batch (no frozen file edits)

## 3. What Phase2 Does NOT Cover

| Category | Phase | Status |
|---|---|---|
| HIGH_RISK_WRITE scripts | Phase3 | FROZEN |
| HIGH_RISK_RUNTIME scripts | Phase4 | FROZEN |
| `core/live_runner.py` | — | FROZEN |
| Runtime integration | Phase4 | NOT STARTED |
| Planner integration | — | NOT STARTED |
| Live trading paths | — | NOT STARTED |

## 4. Recommended Exit Point

| Exit Point | Coverage | Condition |
|---|---|---|
| **Minimum viable** | batch6 (30 scripts, 73.2%) | Stakeholder approval required |
| **Standard** | batch9 (41 scripts, 100%) | All targets met |
| **Early exit** | Any batch | Stakeholder decides coverage sufficient |

Early exit requires documented stakeholder approval and outstanding scripts tracked in backlog for Phase3/4 pickup.

## 5. Post-Phase2

### Phase3 — HIGH_RISK_WRITE

- Unfreeze + guard HIGH_RISK_WRITE scripts
- Requires explicit unfreeze decision
- Each script: additional write-path guard tests
- Not started without approval

### Phase4 — HIGH_RISK_RUNTIME

- Unfreeze + guard HIGH_RISK_RUNTIME scripts
- Requires explicit unfreeze decision
- Includes runtime integration + planner hooks
- Not started without approval

### Gate Rule

Neither Phase3 nor Phase4 starts without explicit unfreeze decision recorded in `PROJECT_STATE.md`.

## 6. Validation Command

```bash
# Full regression
python -m pytest tests/ -v --tb=short

# Guard-only tests
python -m pytest tests/test_execution_guards*.py -v

# Frozen boundary check
git diff --name-only | grep -v '^docs/' | grep -v '^tests/' || echo "CLEAN"
```
