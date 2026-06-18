# Phase 10O: Web Console Positions / Scorecard Pages

## Summary

Enhanced local shadow web console with data views: positions table, scorecard table, sample gate card, and recent actions.

## Files Modified

- `core/paper_trading/shadow_web_console.py` — added:
  - `load_latest_positions()` — loads positions from quarantine JSON
  - `load_latest_scorecard()` — loads scorecard data
  - `load_latest_sample_gate()` — loads sample gate data
  - `load_recent_actions()` — loads action log from JSONL
  - `render_positions_table()` — HTML table with stats cards
  - `render_scorecard_table()` — HTML table with insufficient sample warning
  - `render_sample_gate_card()` — status card
  - `render_recent_actions_table()` — action log table
  - `_escape_html()` — HTML escaping for all user data
  - Updated `render_dashboard_html()` to accept and render positions/scorecard/gate/actions

- `scripts/run_shadow_web_console.py` — updated to load and pass new data sections

- `tests/unit/test_shadow_web_console.py` — added 28 new tests:
  - TestLoadPositions, TestLoadScorecard, TestLoadSampleGate, TestLoadRecentActions
  - TestRenderPositionsTable (5 tests)
  - TestRenderScorecardTable (3 tests)
  - TestRenderSampleGateCard (3 tests)
  - TestRenderRecentActions (2 tests)
  - TestDashboardSections (7 tests)

## Dashboard Sections

1. **Status** — sample_status, testnet_gate_status, positions counts, lifecycle status
2. **Actions** — 4 buttons for shadow-only scripts
3. **Reports** — links to latest report files
4. **Paper Positions** — stats cards (OPEN/TP/SL/Timeout/Quarantined/Clean) + full table
5. **Strategy Scorecard** — per-strategy metrics + insufficient sample warning
6. **Sample Gate** — gate status card with reasons
7. **Recent Actions** — last 10 action logs

## Safety

- Local-only binding enforced
- All HTML output escaped via `html.escape()`
- No path traversal in report viewer
- No testnet_ready=true / live_ready=true in output
- No orders, accounts, secrets, testnet, live

## Commit Plan

```bash
git add core/paper_trading/shadow_web_console.py tests/unit/test_shadow_web_console.py
git commit -m "Add web console positions and scorecard views"

git add scripts/run_shadow_web_console.py tests/unit/test_run_shadow_web_console_script.py
git commit -m "Keep web console runner local-only"

git add docs/PHASE10O_WEB_CONSOLE_POSITION_SCORECARD_RESULT.md
git commit -m "Document web console positions scorecard"
```
