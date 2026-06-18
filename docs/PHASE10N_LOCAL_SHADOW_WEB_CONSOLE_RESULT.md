# Phase 10N: Local Shadow Trading Web Console

## Summary

Created a local-only web console for shadow trading operations. Replaces command-line operations with a browser-based dashboard.

## Files Added

- `core/paper_trading/shadow_web_console.py` — core module
  - `load_console_status()` — loads status from reports
  - `render_dashboard_html()` — renders HTML dashboard
  - `run_allowed_action()` — runs allowed actions via subprocess
  - `render_report_file()` — safely reads report files
  - `is_safe_report_name()` — path traversal guard
  - `append_action_log()` — logs actions to JSONL

- `scripts/run_shadow_web_console.py` — runner script
  - HTTP server on 127.0.0.1:8765
  - Dashboard page (GET /)
  - Action endpoints (POST /action/...)
  - Report viewer (GET /report?name=...)
  - `--smoke-render` for HTML validation without starting server

- `tests/unit/test_shadow_web_console.py` — 30 tests
- `tests/unit/test_run_shadow_web_console_script.py` — 16 tests
- `docs/SHADOW_WEB_CONSOLE_RUNBOOK.md` — operator guide
- `docs/PHASE10N_LOCAL_SHADOW_WEB_CONSOLE_RESULT.md` — this file

## Dashboard Features

- Status grid: sample_status, testnet_gate_status, positions counts
- Action buttons: lifecycle, update-only, sample gate, status
- Report links: lifecycle, update-only, gate, scorecard
- Safety footer: paper-only, shadow-only, local-only, no order, no testnet, no live

## Safety

- Local-only binding (127.0.0.1/localhost enforced)
- Non-local host → reject startup
- No public deployment
- No login/cookies/sessions
- No account sync
- No order path
- No testnet/live
- No secret/.env reads
- No websocket
- No daemon/scheduler
- Fixed action allowlist (no user-defined commands)
- Report path traversal guard
- subprocess with shell=False, timeout=300

## Run Command

```bash
python3 scripts/run_shadow_web_console.py
```

Open: http://127.0.0.1:8765

## Commit Plan

```bash
git add core/paper_trading/shadow_web_console.py tests/unit/test_shadow_web_console.py
git commit -m "Add local shadow web console core"

git add scripts/run_shadow_web_console.py tests/unit/test_run_shadow_web_console_script.py
git commit -m "Add local shadow web console runner"

git add docs/SHADOW_WEB_CONSOLE_RUNBOOK.md docs/PHASE10N_LOCAL_SHADOW_WEB_CONSOLE_RESULT.md
git commit -m "Document local shadow web console"
```
