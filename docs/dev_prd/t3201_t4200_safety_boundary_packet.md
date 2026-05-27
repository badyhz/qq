# T3201-T4200 Safety Boundary Packet

## Safety Rules

### Hard Constraints
1. **release_hold = "HOLD"** — Always. No exceptions.
2. **No network calls** — All backtest modules are pure or file-I/O only.
3. **No live trading** — No exchange clients, no order submission.
4. **No secrets** — No credentials, API keys, or tokens.
5. **Frozen dataclasses** — All core models are immutable.
6. **Explicit git add** — No `git add .` permitted.

### Forbidden Files
Never touch, import, or commit:
- `core/live_runner.py`
- `scripts/live_playbook.py`
- `scripts/submit_approved_candidates.py`
- `scripts/run_testnet_order_smoke.py`
- `scripts/run_signal_testnet_trial.py`
- `scripts/run_spot_testnet_acceptance.py`
- `scripts/safe_flatten_testnet_symbol.py`
- `scripts/replay_shadow_order_plans_as_testnet_dry.py`
- `scripts/submit_replayed_testnet_payload.py`
- All MEDIUM-risk scripts

### No-Network Guarantee

Verification:
```bash
grep -r "requests\.\|urllib\.\|httpx\.\|aiohttp\." core/offline_*.py core/historical_*.py core/walk_forward_*.py
# Expected: no matches
```

No module in the backtest lab imports or uses:
- `requests`, `urllib`, `httpx`, `aiohttp`
- `websocket`, `socket`
- Any network library

### HOLD Invariant

The `release_hold = "HOLD"` value is hardcoded in:
- `offline_shadow_bundle_builder.py`: manifest always sets `"release_hold": "HOLD"`
- `offline_shadow_report_renderer.py`: reports always display HOLD banner
- All test assertions verify HOLD is present

No code path can change release_hold to any value other than "HOLD".

## Import Boundary

Backtest lab modules may only import:
- Other backtest lab modules (core/offline_*, core/historical_*, core/walk_forward_*)
- Standard library (math, csv, json, hashlib, dataclasses, enum, typing, statistics)
- No external packages (pandas, numpy, requests, etc.)

Exception: `core/signal_engine.py` may import `utils.indicators` but backtest
modules do not import signal_engine (they use their own signal engine).

## Frozen File Boundary

22 frozen files exist in the repository. The backtest lab does not:
- Modify any frozen file
- Import from any frozen file
- Reference any frozen file in tests

## Test Isolation

All backtest tests:
- Use fixture data (no live data)
- Make no network calls
- Do not modify production state
- Are deterministic (no randomness, no timestamps)
