# T1521-T1600 Safety Boundary Packet

## Frozen Files List

The following files are frozen and must not be modified by automated tasks:

- `core/live_runner.py`
- `core/single_call_recorder.py`
- `core/evidence_recorder.py`
- `scripts/run_signal_testnet_trial.py`
- `scripts/run_spot_testnet_acceptance.py`
- `scripts/run_testnet_order_smoke.py`
- `scripts/safe_flatten_testnet_symbol.py`
- `scripts/submit_approved_candidates.py`
- `scripts/submit_replayed_testnet_payload.py`

## T1521-T1600 Scope

This batch produces documentation and tests only. No code modules, no runtime artifacts.

### Deliverables

- 5 new documentation files (CLI, materializer, acceptance, safety, closeout)
- 2 updated documentation files (task queue, current state)
- 1 compatibility test file

## Forbidden Imports

Tasks in T1521-T1600 must NOT import:

- `binance.client` or any exchange SDK
- `ccxt` or any exchange abstraction
- `requests` for exchange API calls
- Any module containing `submit`, `execute`, or `order` in live context
- `dotenv` or `os.environ` for secret retrieval in runtime context

## No Live Trading Rule

No task in this range may:

1. Submit orders to any exchange
2. Connect to exchange WebSocket or REST endpoints
3. Read or write API keys, secrets, or credentials
4. Invoke `live_runner.py` or any testnet submission script
5. Modify frozen files listed above

## No Submit Rule

All artifacts in T1521-T1600 are documentation and test only. No code in this range may:

- Call any exchange submission function
- Write to any exchange-facing network socket
- Trigger any order placement workflow

## Frozen Backlog Boundary

- All 9 HIGH-risk files remain frozen throughout T1521-T1600
- Documentation is advisory only; no modifications to frozen files
- CLI and materializer specs describe read-only interfaces
- No runtime integration in this batch

## Medium Operational Boundary

- All 22 MEDIUM-risk files governed by medium-risk policy
- Dry-run only: no live execution of operational scripts
- No credential access from operational scripts
- No network calls to exchange endpoints from operational scripts

## Release Hold

Status: HOLD. No live trading authorization. No autonomous progression beyond T1600.

## Enforcement

Violation of any boundary above is a hard stop. Task must be reverted and escalated to human review.
