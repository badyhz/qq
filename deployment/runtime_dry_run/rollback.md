# Rollback Procedure

## If E2E pipeline fails:

1. Check `data/runtime/e2e/run_manifest.json` for error details
2. Review `reports/system_dry_run_e2e_report.md`
3. Fix issue
4. Re-run: `PYTHONPATH=. python3 scripts/run_system_dry_run_e2e.py`

## If dashboard is stale:

1. Re-run: `PYTHONPATH=. python3 scripts/run_runtime_operator_console.py`
2. Verify `reports/operator_dashboard.html` updated

## Full reset:

1. Delete `data/runtime/` directory
2. Re-run E2E pipeline
