# Execution Guard Phase 2 Metrics

> Single source of truth for Phase 2 guard metrics.
> Cross-check other docs against this file.

## Current State

- 41 guarded scripts (batch1-9 complete)
- 0 SAFE remaining (all eligible guarded)
- 1 KEEP_NEEDS_REVIEW (review_trade_logic_evolution_with_klines.py)
- 219 NOT_ELIGIBLE
- 22 frozen files (21 scripts + core/live_runner.py)

## Batch Status

| Batch | Scripts | Tests | Status |
|---|---|---|---|
| Batch1 | 5 | 30 | COMPLETE |
| Batch2 | 5 | 30 | COMPLETE |
| Batch3 | 5 | 24+6 skip | COMPLETE |
| Batch4 | 5 | 30 | COMPLETE |
| Batch5 | 5 | 30 | COMPLETE |
| Batch6 | 5 | 30 | COMPLETE |
| Batch7 | 5 | 30 | COMPLETE |
| Batch8 | 5 | 30 | COMPLETE |
| Batch9 | 1 | 6 | COMPLETE |

## Coverage Metrics

- guarded / (guarded + unguarded SAFE) = 41/41 = 100.0%
- guarded / total scripts with main() = 41/185 = 22.1%
- guarded / non-frozen = 41/331 = 12.3%

## Test Baseline

- Guard core (Phase0): 124 tests
- Batch1: 30 tests
- Batch2: 30 tests
- Batch3: 24 pass + 6 skip
- Batch4: 30 tests
- Batch5: 30 tests
- Batch6: 30 tests
- Batch7: 30 tests
- Batch8: 30 tests
- Batch9: 6 tests
- Total guard tests: ~374
- Regression suite: 124 tests
- Latest full run: ~374 guard + 124 regression = ~498 total

## Definitions

| Term | Meaning |
|---|---|
| SAFE_READONLY_CANDIDATE | Scripts eligible for guard injection |
| PROMOTE_TO_SAFE | Scripts re-audited from NEEDS_REVIEW to SAFE |
| KEEP_NEEDS_REVIEW | Scripts with residual risk |
| NOT_ELIGIBLE | Scripts that import dangerous modules or have execution roles |
| FROZEN | 22 high-risk files, no modification allowed |

## Source-of-Truth Commands

```bash
# Count guarded scripts
grep -rl "assert_dry_run_required" scripts/*.py | wc -l

# Count guard test files
ls tests/unit/test_*_guard.py | wc -l

# Count frozen files
git status --short | grep "^??" | grep -c "frozen\|live_runner\|submit\|cancel\|flatten"

# Run full test suite
.venv/bin/python -m pytest tests/unit/test_*_guard.py tests/unit/test_execution_guards.py tests/unit/test_execution_guard_schema.py tests/unit/test_execution_guard_contract.py
```

## Warning

Docs may lag actual git state unless manually synced. This metrics page is the authoritative reference -- cross-check other docs against it.
