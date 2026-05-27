# T1161-T1260 Safety Boundary Packet

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

## Forbidden Imports

Tasks in T1161-T1260 must NOT import:

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

All artifacts in T1161-T1260 are governance-layer only. No code in this range may:

- Call any exchange submission function
- Write to any exchange-facing network socket
- Trigger any order placement workflow

## Enforcement

Violation of any boundary above is a hard stop. Task must be reverted and escalated to human review.
