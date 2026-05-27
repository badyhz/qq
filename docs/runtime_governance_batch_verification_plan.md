# Runtime Governance Batch Verification Plan

T823 — deterministic verification commands for runtime governance.

| # | Command ID | Command | Purpose | Required |
|---|------------|---------|---------|----------|
| 1 | runtime_governance_tests | `python3 -m pytest tests/unit/test_runtime_governance_*.py -q` | runtime governance tests | yes |
| 2 | governance_failure_tests | `python3 -m pytest tests/unit/test_governance_failure_*.py -q` | governance failure tests | yes |
| 3 | core_regression | `python3 -m pytest tests/unit/test_adapter_safety.py tests/unit/test_workflow_safety.py tests/unit/test_governance_state.py -q` | core regression | yes |
| 4 | git_status | `git status --short` | check uncommitted changes | yes |
| 5 | no_large_log | `echo 'Do not read full CSV/JSONL/log files'` | reminder | yes |
