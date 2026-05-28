# Offline Research Preflight Checklist

## CL-PREFLIGHT-001: Python Environment
- **ID:** CL-PREFLIGHT-001
- **Required:** Required
- **Evidence path:** `python3 --version`
- **Pass condition:** Python 3.10+ installed
- **Fail condition:** Python version < 3.10 or missing
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-PREFLIGHT-002: Virtual Environment
- **ID:** CL-PREFLIGHT-002
- **Required:** Required
- **Evidence path:** `.venv/`
- **Pass condition:** `.venv` directory exists and is activated
- **Fail condition:** `.venv` missing or not activated
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-PREFLIGHT-003: Fixtures Present
- **ID:** CL-PREFLIGHT-003
- **Required:** Required
- **Evidence path:** `tests/fixtures/historical_backtest_lab/`
- **Pass condition:** Directory exists with CSV files
- **Fail condition:** Directory missing or empty
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-PREFLIGHT-004: Experiment Catalog
- **ID:** CL-PREFLIGHT-004
- **Required:** Required
- **Evidence path:** `tests/fixtures/offline_research_experiment_library/experiment_catalog.json`
- **Pass condition:** File exists and is valid JSON with 20+ experiments
- **Fail condition:** File missing or invalid
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-PREFLIGHT-005: Governance Validation
- **ID:** CL-PREFLIGHT-005
- **Required:** Required
- **Evidence path:** `/tmp/offline_research_governance_validation/governance_validation.json`
- **Pass condition:** `valid = true`
- **Fail condition:** `valid = false`
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-PREFLIGHT-006: Experiment Library Validation
- **ID:** CL-PREFLIGHT-006
- **Required:** Required
- **Evidence path:** `/tmp/offline_research_experiment_library_validation/experiment_library_validation.json`
- **Pass condition:** `valid = true`
- **Fail condition:** `valid = false`
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-PREFLIGHT-007: Safety Regression Tests
- **ID:** CL-PREFLIGHT-007
- **Required:** Required
- **Evidence path:** pytest output
- **Pass condition:** All safety regression tests pass
- **Fail condition:** Any safety regression test fails
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-PREFLIGHT-008: Git Status Clean
- **ID:** CL-PREFLIGHT-008
- **Required:** Required
- **Evidence path:** `git status --short`
- **Pass condition:** No unwanted staged files
- **Fail condition:** Unwanted files staged (especially untracked live/testnet/shadow)
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-PREFLIGHT-009: No Network
- **ID:** CL-PREFLIGHT-009
- **Required:** Required
- **Evidence path:** Module imports
- **Pass condition:** No network imports (requests, httpx, aiohttp, websocket)
- **Fail condition:** Network imports detected
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## CL-PREFLIGHT-010: No Exchange
- **ID:** CL-PREFLIGHT-010
- **Required:** Required
- **Evidence path:** Module imports
- **Pass condition:** No exchange imports (binance, ccxt)
- **Fail condition:** Exchange imports detected
- **Human note:** _______________
- **Safety boundary:** release_hold = HOLD

## Safety Reminder
All preflight checks must pass before running the offline pipeline. release_hold must remain HOLD. If any check fails, do not proceed.
