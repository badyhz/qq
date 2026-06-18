# Phase 10P: Web Console Strategy Switchboard Page

## Summary

Added read-only strategy switchboard to local web console. Displays strategy config from `config/strategies.yaml` merged with scorecard data.

## Files Modified

- `core/paper_trading/shadow_web_console.py` — added:
  - `load_strategy_config()` — reads YAML config
  - `load_strategy_switchboard()` — merges config with scorecard
  - `render_strategy_switchboard_table()` — read-only HTML table
  - Updated `render_dashboard_html()` to accept and render switchboard

- `scripts/run_shadow_web_console.py` — updated to load and pass switchboard data

- `tests/unit/test_shadow_web_console.py` — added 17 new tests (97 total)

## Strategy Switchboard Display

| Field | Source |
|-------|--------|
| strategy_id | config |
| enabled | config (ON=green, OFF=gray) |
| strategy_type | config |
| mode | config |
| data_api | config |
| symbols count | config |
| symbols | config (max 20, +N more) |
| timeframes | config |
| auto_send | config (true=red warning) |
| sample_status | scorecard |
| strategy_status | scorecard |
| strategy_score | scorecard |

## Safety

- Read-only: no config write, no POST enable/disable
- No strategy config mutation
- Local-only binding
- No testnet/live
- No orders/accounts/secrets
- All HTML output escaped

## Commit Plan

```bash
git add core/paper_trading/shadow_web_console.py tests/unit/test_shadow_web_console.py
git commit -m "Add web console strategy switchboard view"

git add scripts/run_shadow_web_console.py tests/unit/test_run_shadow_web_console_script.py
git commit -m "Render strategy switchboard in web console"

git add docs/PHASE10P_WEB_CONSOLE_STRATEGY_SWITCHBOARD_RESULT.md
git commit -m "Document web console strategy switchboard"
```
