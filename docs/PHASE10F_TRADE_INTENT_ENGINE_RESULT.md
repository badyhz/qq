# Phase 10F Strategy Candidate → Trade Intent Engine Result

**Date:** 2026-06-18
**Status:** PHASE10F_TRADE_INTENT_ENGINE_READY

## Summary

Phase 10F completed. Strategy candidates converted to shadow-only TradeIntents with risk gate validation.

- Compileall: PASS
- Unit tests: 64 passed
- Offline smoke: PASS (21 intents, 13 SHADOW_READY, 0 BLOCKED, 8 INVALID)
- Real public readonly smoke: PASS (5 intents, 0 SHADOW_READY, 0 BLOCKED, 5 INVALID)

## Architecture

```
strategy_runner (Phase 10D)       trade_intent (Phase 10F)
─────────────────────────        ─────────────────────────
strategy_payload_input.json ──→  trade_intent.py
                                  build_trade_intent()
                                        │
                                        ▼
                                 trade_intent_risk_gate.py
                                  validate_trade_intent()
                                        │
                                        ▼
                                 trade_intents.json/md/jsonl
```

## Files

### New Modules
- `core/paper_trading/trade_intent.py`
  - `TradeIntent` dataclass (shadow-only)
  - `build_trade_intent(plan, date_str, paper_equity, max_risk_pct)`
  - Direction mapping: LONG_OBSERVE→LONG, SHORT_OBSERVE→SHORT
  - Position sizing: risk_amount / risk_per_unit

- `core/paper_trading/trade_intent_risk_gate.py`
  - `RiskGateResult` dataclass
  - `validate_trade_intent(intent)` → PASS/BLOCK/INVALID
  - Checks: rr_ratio, risk_distance, SL/TP vs entry, max_risk, forbidden fields

### New Script
- `scripts/run_strategy_trade_intents.py`
  - Reads strategy_payload_input.json
  - Outputs trade_intents.json, trade_intents.md, trade_intent_ledger.jsonl

### New Tests
- `tests/unit/test_paper_trade_intent.py` (24 tests)
- `tests/unit/test_paper_trade_intent_risk_gate.py` (26 tests)
- `tests/unit/test_run_strategy_trade_intents_script.py` (14 tests)

## Usage

```bash
# Step 1: Generate strategy candidates
python3 scripts/run_enabled_strategies.py --allow-public-http

# Step 2: Generate trade intents
python3 scripts/run_strategy_trade_intents.py

# Custom parameters
python3 scripts/run_strategy_trade_intents.py --paper-equity-preview 20000 --max-risk-pct 0.3
python3 scripts/run_strategy_trade_intents.py --strategy weak_short_watch
python3 scripts/run_strategy_trade_intents.py --date 2026-06-18
```

## Intent Status Rules

| Condition | Status |
|-----------|--------|
| side == NO_TRADE | INVALID |
| entry_price <= 0 | INVALID |
| stop_loss <= 0 | BLOCKED |
| take_profit <= 0 | BLOCKED |
| rr_ratio < 1.5 | BLOCKED |
| risk_distance > 5% | BLOCKED |
| max_risk_pct > 0.5% | BLOCKED |
| LONG: SL >= entry | BLOCKED |
| SHORT: SL <= entry | BLOCKED |
| All checks pass | SHADOW_READY |

## Risk Gate Rules

1. rr_ratio >= 1.5
2. risk_distance 0-5%
3. reward > risk
4. max_risk_pct <= 0.5%
5. LONG: SL < entry, TP > entry
6. SHORT: SL > entry, TP < entry
7. execution_mode == shadow_only
8. No forbidden fields (account_id, api_key, etc.)

## Smoke Results

### Offline (mock data)
- Total: 21 intents
- SHADOW_READY: 13
- BLOCKED: 0
- INVALID: 8

### Real Public HTTP
- Total: 5 intents
- SHADOW_READY: 0
- BLOCKED: 0
- INVALID: 5
- Reason: weak_short candidates have TP=0.0

## Safety Confirmation

- Paper-only: YES
- Shadow-only: YES (execution_mode always shadow_only)
- No order: YES
- No account: YES
- No testnet: YES
- No live: YES
- No websocket: YES
- No secret: YES
- No .env: YES
- No real Feishu send: YES
- No --allow-send: YES
- No --webhook-url: YES
- No env reads: YES
- No order_executor: YES
- No account_sync: YES
- Manual execution remains impossible: YES
