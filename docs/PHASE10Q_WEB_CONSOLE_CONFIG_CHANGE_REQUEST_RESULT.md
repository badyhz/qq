# Phase 10Q: Web Console Strategy Config Change Request

## Summary

Added config change request form to local web console. Generates draft request files — never writes `config/strategies.yaml` directly.

## Files Modified

- `core/paper_trading/shadow_web_console.py` — added:
  - `ALLOWED_TIMEFRAMES` — set of valid timeframe strings
  - `validate_config_change_request()` — validates form input against allowlists
  - `create_config_change_request()` — creates request dict with PENDING_HUMAN_REVIEW status
  - `append_config_change_request()` — appends to JSONL and writes latest markdown
  - `render_config_change_form()` — HTML form with strategy select, enabled, symbols, timeframes, reason
  - `render_config_change_result()` — HTML result display
  - Updated `render_dashboard_html()` to accept `config_change_result`

- `scripts/run_shadow_web_console.py` — updated:
  - Added `_handle_config_change()` POST handler
  - Added `/action/request-config-change` route in `do_POST()`
  - Updated imports for config change functions

- `tests/unit/test_shadow_web_console.py` — added 14 new tests (113 total):
  - TestValidateConfigChangeRequest (7 tests)
  - TestCreateConfigChangeRequest (1 test)
  - TestAppendConfigChangeRequest (1 test)
  - TestRenderConfigChangeForm (3 tests)
  - TestRenderConfigChangeResult (1 test)
  - TestDashboardConfigChange (1 test)

## Config Change Request Flow

1. User fills form: strategy_id, requested_enabled, symbols, timeframes, reason
2. Form POSTs to `/action/request-config-change`
3. `validate_config_change_request()` checks against allowlists
4. `create_config_change_request()` creates dict with `status=PENDING_HUMAN_REVIEW`, `config_written=False`
5. `append_config_change_request()` writes to:
   - `reports/strategies/config_change_requests.jsonl` (append)
   - `reports/strategies/latest_config_change_request.md` (overwrite)
6. Result HTML returned to browser

## Validation Rules

| Field | Rule |
|-------|------|
| strategy_id | Required, must exist in switchboard |
| requested_enabled | Must be `no_change`, `true`, or `false` |
| symbols | Comma-separated, each `[A-Z0-9_\-/]+`, max 30 chars, max 100 symbols |
| timeframes | Comma-separated, each must be in ALLOWED_TIMEFRAMES |
| reason | Required, max 500 chars |

## Safety

- Draft-only: generates request files, never writes config
- `config_written=False` in all requests
- `status=PENDING_HUMAN_REVIEW` — requires human approval
- Form notice: "不会直接修改 config/strategies.yaml"
- Result notice: "本文件只是变更草案"
- All HTML output escaped
- Local-only binding

## Commit Plan

```bash
git add core/paper_trading/shadow_web_console.py tests/unit/test_shadow_web_console.py
git commit -m "Add web console config change requests"

git add scripts/run_shadow_web_console.py tests/unit/test_run_shadow_web_console_script.py
git commit -m "Handle config change request form"

git add docs/PHASE10Q_WEB_CONSOLE_CONFIG_CHANGE_REQUEST_RESULT.md
git commit -m "Document web console config change requests"
```
