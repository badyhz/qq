# Offline Research Stack Safety Manual

## Core Safety Properties

### release_hold = HOLD
The release hold is the master safety control. While release_hold is HOLD:
- No live trading can occur
- No testnet submission can occur
- No runtime integration is active
- No planner integration is active
- All research output is advisory only

**release_hold must never be changed without explicit human approval.**

### Advisory Only
All research output is advisory only. Research results do not authorize:
- Live trading
- Testnet submission
- Order placement
- Order cancellation
- Position flattening
- Runtime activation
- Planner integration

### Human Review Required
All research artifacts require human review before any promotion. No auto_promotion mechanism exists.

## Safety Flags

All experiments and artifacts must include these safety flags:
- `release_hold = "HOLD"`
- `advisory_only = true`
- `human_review_required = true`
- `no_live = true`
- `no_submit = true`
- `no_exchange = true`
- `no_network = true`
- `no_runtime_integration = true`
- `no_planner_integration = true`

## Forbidden Actions

### Never Do These
- Enable live trading
- Submit orders (live or testnet)
- Cancel orders
- Flatten positions
- Connect to exchange
- Make network calls
- Integrate with runtime
- Integrate with planner
- Auto-promote research results
- Use `git add .`
- Stage untracked live/testnet/shadow files

### Forbidden Imports
- `requests`, `httpx`, `aiohttp`, `urllib`, `websocket`
- `binance`, `ccxt`
- `live_trading`, `live_submit`
- `testnet_submit`, `testnet_client`

### Forbidden Commands in Experiments
- `submit_order`
- `cancel_order`
- `flatten_position`
- `place_order`
- `testnet_submit`
- `live_trading`
- `runtime_start`
- `planner_run`
- `exchange_connect`
- `binance_client`

## Untracked External State

Pre-existing untracked files in the working tree are external state:
- `core/live_runner.py`
- `scripts/live_playbook.py`
- Various `scripts/run_*.py` (testnet/shadow)
- `research/` directory

Do NOT stage, import, execute, or modify these files.

## Emergency Procedures

If safety boundary is violated:
1. STOP immediately
2. Do not commit
3. Run governance validator
4. Assess damage
5. Follow recovery docs
6. Escalate to human operator

## Validation Commands

```bash
# Validate governance
python3 scripts/validate_offline_research_stack_docs.py \
  --docs-root docs \
  --output-dir /tmp/offline_research_governance_validation \
  --strict --release-hold HOLD

# Validate experiment library
python3 scripts/validate_offline_research_experiment_library.py \
  --catalog tests/fixtures/offline_research_experiment_library/experiment_catalog.json \
  --output-dir /tmp/offline_research_experiment_library_validation \
  --strict --release-hold HOLD

# Full test suite
PYTHONPATH=. .venv/bin/pytest -q
```

## Signoff Decisions

### Allowed
- REJECT
- REQUEST_MORE_RESEARCH
- ACCEPT_ADVISORY_RESEARCH_ONLY

### Forbidden
- APPROVE_LIVE
- APPROVE_TESTNET_SUBMIT
- APPROVE_RUNTIME
- APPROVE_PLANNER_INTEGRATION
- AUTO_PROMOTE

## No Auto-Promotion Statement

There is no no_auto_promotion path in the offline research stack. No auto-promotion mechanism exists. No artifact can move from offline/research to live/testnet/runtime without explicit human approval and release_hold lift.
