# Dirty Workspace High-Risk Freeze Inventory

Date: 2026-05-27
Context: Post T961-T1060 closeout. Pre-existing untracked files in workspace.
Status: FROZEN — no auto-commit, no auto-wire, no auto-run.

## Global Freeze Rule

These files are under **HUMAN_REVIEW_ONLY** freeze. No agent may:
- auto-commit
- auto-wire into any pipeline
- auto-run or execute
- connect to live exchange
- access credentials
- submit orders

## Release Hold

release_hold = **HOLD**
No live trading authorization exists.

## Safety Statement

No runtime integration. No planner integration. No live execution.
Read-only design artifacts only for PRD tasks T1061+.

## Frozen Inventory

### 1. core/live_runner.py

- path: `core/live_runner.py`
- tracked/untracked: **untracked**
- risk level: **HIGH**
- why: `LiveRunner` class wraps `ExecutionEngine.run_once()` with failure policy and preflight readiness checks. Direct runtime execution entry point.
- imports: `core.failure_policy`, `core.preflight`
- allowed action: **HUMAN_REVIEW_ONLY**
- forbidden: auto-commit, auto-wire, auto-run, live-submit, credential access

### 2. scripts/live_playbook.py

- path: `scripts/live_playbook.py`
- tracked/untracked: **untracked**
- risk level: **HIGH**
- why: CLI playbook with `--mode` supporting `dry-run`, `testnet`, `live`. Imports `ExecutionEngine`, `OrderManager`, `run_preflight_bundle`, `run_testnet_order_smoke_bundle`. Can trigger real execution in live mode.
- imports: `core.execution`, `core.order_manager`, `scripts.run_preflight_check`, `scripts.run_testnet_order_smoke`
- allowed action: **HUMAN_REVIEW_ONLY**
- forbidden: auto-commit, auto-wire, auto-run, live-submit, credential access

### 3. scripts/submit_approved_candidates.py

- path: `scripts/submit_approved_candidates.py`
- tracked/untracked: **untracked**
- risk level: **HIGH**
- why: Loads execution candidates, validates via `account_risk_guard`, runs `pre_submit_strategy_gate`, triggers `run_replay_submit_batch`. Direct order submission path.
- imports: `core.account_risk_guard`, `core.execution_candidate_queue`, `core.risk_event_logger`, `core.trade_logger`, `scripts.check_testnet_state`, `scripts.generate_testnet_acceptance_report`, `scripts.pre_submit_strategy_gate`, `scripts.run_replay_submit_batch`
- allowed action: **HUMAN_REVIEW_ONLY**
- forbidden: auto-commit, auto-wire, auto-run, live-submit, credential access

### 4. scripts/run_testnet_order_smoke.py

- path: `scripts/run_testnet_order_smoke.py`
- tracked/untracked: **untracked**
- risk level: **HIGH**
- why: Builds `BinanceConnector` with `mode="live"`, reads `BINANCE_API_KEY`/`BINANCE_API_SECRET` from env. Can place testnet orders via `ExecutionEngine` + `OrderManager`.
- imports: `core.binance_connector`, `core.execution`, `core.order_manager`
- allowed action: **HUMAN_REVIEW_ONLY**
- forbidden: auto-commit, auto-wire, auto-run, live-submit, credential access

### 5. scripts/run_signal_testnet_trial.py

- path: `scripts/run_signal_testnet_trial.py`
- tracked/untracked: **untracked**
- risk level: **HIGH**
- why: Builds `BinanceConnector` with `mode="live"`, reads API credentials from env. Runs signal engine against testnet with real connector.
- imports: `core.binance_connector`, `core.execution`, `core.order_manager`
- allowed action: **HUMAN_REVIEW_ONLY**
- forbidden: auto-commit, auto-wire, auto-run, live-submit, credential access

### 6. scripts/run_spot_testnet_acceptance.py

- path: `scripts/run_spot_testnet_acceptance.py`
- tracked/untracked: **untracked**
- risk level: **HIGH**
- why: Builds `BinanceConnector` with `mode="live"`, reads API credentials from env. Runs spot testnet acceptance with real connector.
- imports: `core.binance_connector`, `core.execution`, `core.order_manager`
- allowed action: **HUMAN_REVIEW_ONLY**
- forbidden: auto-commit, auto-wire, auto-run, live-submit, credential access

### 7. scripts/safe_flatten_testnet_symbol.py

- path: `scripts/safe_flatten_testnet_symbol.py`
- tracked/untracked: **untracked**
- risk level: **HIGH**
- why: Uses `BinanceFuturesTestnetClient` to place market orders for position flattening. Validates via `execution_safety`. Direct order placement on testnet.
- imports: `core.binance_testnet_client`, `core.execution_safety`, `core.risk_event_logger`, `core.trade_logger`
- allowed action: **HUMAN_REVIEW_ONLY**
- forbidden: auto-commit, auto-wire, auto-run, live-submit, credential access

### 8. scripts/replay_shadow_order_plans_as_testnet_dry.py

- path: `scripts/replay_shadow_order_plans_as_testnet_dry.py`
- tracked/untracked: **untracked**
- risk level: **HIGH**
- why: Reads shadow order plans, fetches public market data, computes quantity models, builds testnet dry payloads. Bridge between shadow plans and testnet execution.
- imports: `core.binance_testnet_client`, `core.public_market_data`, `core.risk_manager`, `core.trade_logger`
- allowed action: **HUMAN_REVIEW_ONLY**
- forbidden: auto-commit, auto-wire, auto-run, live-submit, credential access

### 9. scripts/submit_replayed_testnet_payload.py

- path: `scripts/submit_replayed_testnet_payload.py`
- tracked/untracked: **untracked**
- risk level: **HIGH**
- why: Builds and submits orders to `demo-fapi.binance.com` via `BinanceFuturesTestnetClient`. Validates via `execution_safety`. Direct testnet order submission.
- imports: `core.binance_testnet_client`, `core.execution_safety`, `core.risk_event_logger`, `core.trade_logger`
- allowed action: **HUMAN_REVIEW_ONLY**
- forbidden: auto-commit, auto-wire, auto-run, live-submit, credential access

## Human Review Checklist

Before any of these files can be committed, a human must confirm:

- [ ] File is not a live trading path
- [ ] File does not access real credentials
- [ ] File is testnet-only or dry-run-only
- [ ] File has been reviewed line-by-line
- [ ] File has passing tests
- [ ] File does not bypass risk controls
- [ ] File does not connect to production exchange
- [ ] Release hold has been explicitly lifted by human
- [ ] Commit is approved by human operator
