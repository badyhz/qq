# Post e407cb3 Remaining Workspace Review

**Date:** 2026-06-16
**Status:** REVIEW ONLY - no git add, commit, push, tag, deploy, testnet, or live action executed
**Baseline:** `e407cb3 Add risk manager margin cap`

## Current State

```text
staged: 0
remaining tracked modified after convergence: 4
untracked: 1716 before these review docs
```

`core/signal_engine.py` was restored to the tracked generic implementation and no longer has a diff.

## Tracked Files

| File | Diff summary | MACD/plugin? | live/testnet/deploy/order? | Decision |
|------|--------------|--------------|-----------------------------|----------|
| `config.yaml` | Keeps only `dry_run_slippage_rate: 0.0005`; removed global MACD params | No | No | KEEP |
| `core/order_manager.py` | Changes live-mode market update path and adds live `TIME_EXIT` handling | No | Yes, live path | REVERT_CANDIDATE / HOLD |
| `core/signal_engine.py` | No remaining diff after convergence | No | No | KEEP AS GENERIC BASELINE |
| `tests/unit/test_signal_engine.py` | Adds generic full short signal generation coverage only; plugin imports removed | No | No | KEEP |
| `utils/indicators.py` | Adds local `ema_series()` and `macd()` helpers; no IO | Supports plugin | No | KEEP |

## MACD Closure Files

| File | Review result | Decision |
|------|---------------|----------|
| `core/market_data_contract.py` | Local OHLCV dataclasses; fixture/mock default; validates `is_live` as invalid | KEEP |
| `core/signal_envelope.py` | Local signal envelope; enforces `dry_run=True`; allowed modes limited to `paper`, `shadow`, `dry_run` | KEEP |
| `core/macd_rebound_signal_plugin.py` | Plugin-local MACD confirmation; wraps generic `SignalEngine`; emits `SignalEnvelope`; no order submission | KEEP |
| `tests/unit/test_market_data_contract.py` | Covers candle, series, batch, metadata validation | KEEP |
| `tests/unit/test_macd_rebound_signal_plugin.py` | Covers plugin creation, dry-run/mode rejection, local MACD context, envelope shape, reset | KEEP |

## Security And Runtime Review

The allowed-scope files were checked for obvious real network, secret, order, deploy, push, and tag patterns. Findings were limited to pre-existing `websocket` configuration keys in `config.yaml`; no new real HTTP, secret read, order submission, deploy, push, or tag logic was found in the MACD closure.

## Final Decisions

KEEP:

```text
config.yaml
tests/unit/test_signal_engine.py
utils/indicators.py
core/market_data_contract.py
core/signal_envelope.py
core/macd_rebound_signal_plugin.py
tests/unit/test_market_data_contract.py
tests/unit/test_macd_rebound_signal_plugin.py
```

KEEP AS GENERIC BASELINE, no staging needed unless it changes again:

```text
core/signal_engine.py
```

REVERT_CANDIDATE / HOLD:

```text
core/order_manager.py
```

Reason: the remaining change touches live-mode behavior. It is outside the dry-run MACD plugin consolidation batch.
