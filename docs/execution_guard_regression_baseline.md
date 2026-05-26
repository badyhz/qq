## Guard Regression Baseline

### Latest Known Results
- Date: post-T656 metrics reconciliation
- Command: `pytest tests/unit/test_*_guard.py tests/unit/test_execution_guards.py tests/unit/test_execution_guard_schema.py tests/unit/test_execution_guard_contract.py`
- Result: 278 pass / 6 skip / 0 fail

### Skipped Tests
| Test File | Skips | Reason | Classification |
|---|---|---|---|
| test_show_trade_stats_guard.py | 6 | pre-existing broken import (dashboard.print_trade_summary never existed) | DEFER |

### Expected Post-Batch6 Baseline
- Guard core: 124 tests (execution_guards + schema + contract)
- Batch1: 30 tests
- Batch2: 30 tests
- Batch3: 24 pass + 6 skip
- Batch4: 30 tests
- Batch5: 30 tests
- Batch6: 30 tests (projected)
- Total guard tests: ~310
- Regression suite: 124 tests
- Full suite: ~434

### Guard Core Regression Suite
| File | Tests | Purpose |
|---|---|---|
| test_execution_guards.py | 62 | Pure helper tests |
| test_execution_guard_schema.py | 38 | Schema validation tests |
| test_execution_guard_contract.py | 24 | Cross-layer contract tests |
| Total | 124 | |

### PASS/PARTIAL/FAIL Interpretation
- PASS: 0 failures, all expected tests run
- PARTIAL: some skips (known/ documented), 0 failures
- FAIL: any failure, any unexpected skip, any frozen file modification

### Commands
```bash
# Full guard suite
.venv/bin/python -m pytest tests/unit/test_*_guard.py tests/unit/test_execution_guards.py tests/unit/test_execution_guard_schema.py tests/unit/test_execution_guard_contract.py -v

# Regression only
.venv/bin/python -m pytest tests/unit/test_execution_guards.py tests/unit/test_execution_guard_schema.py tests/unit/test_execution_guard_contract.py -v

# Count guarded scripts
grep -rl "assert_dry_run_required" scripts/*.py | wc -l

# Count guard test files
ls tests/unit/test_*_guard.py | wc -l
```
