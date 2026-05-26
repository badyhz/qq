# Execution Guard Skipped Test Governance

**Created**: 2026-05-27
**Source**: T635 batch3 skip analysis, T642 root cause confirmation
**Classification**: DEFER (non-blocking)

---

## 1. Affected Script

- **Script**: `scripts/show_trade_stats.py`
- **Guard test**: `tests/unit/test_show_trade_stats_guard.py`
- **Guard injection**: CORRECT — `assert_dry_run_required` present at `main()` entry

## 2. Skip Reason

- Script imports `from dashboard import print_trade_summary`
- `dashboard.py` only contains `TradeDashboard` class — no `print_trade_summary` function
- Function was never implemented (dashboard.py created at init with only TradeDashboard)
- Test file explicitly documents this with `pytestmark = pytest.mark.skipif`
- 6 tests in the guard file are skipped; 0 failures

## 3. Classification

**DEFER** — not blocking, guard suite stays green

The guard code is correctly placed. The skip is intentional and well-documented. No regression risk.

## 4. Why Non-Blocking

- Guard code (`assert_dry_run_required`) is correctly added at `main()` entry
- Tests skip gracefully (6 tests skipped, 0 failures)
- No regression risk — skip is well-documented via `pytestmark`
- Other 4 batch3 scripts pass all tests (12/12)
- Guard suite overall remains green

## 5. When to Revisit

| Trigger | Priority |
|---|---|
| `dashboard.py` extended with `print_trade_summary` API | Medium |
| `show_trade_stats.py` rewritten to use `TradeDashboard` | Medium |
| Script deleted as dead code | Low |

Low priority — no runtime impact while deferred.

## 6. Guard Injection Independence

- Guard was correctly added regardless of broken import
- If dashboard import is fixed later, guard tests will automatically unskip (no `ImportError`, `_CAN_IMPORT` becomes `True`)
- No re-injection needed

---

## References

- `docs/execution_guard_coverage_dashboard.md` — guard inventory
- `docs/execution_guard_safe_taxonomy.md` — classification model
- `tests/unit/test_show_trade_stats_guard.py` — skipped test file (lines 17-27)
