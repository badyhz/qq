# MACD Plugin Architecture Decision

**Date:** 2026-06-16
**Decision:** MACD-specific behavior belongs in a strategy plugin, not in `core/signal_engine.py`.

## Context

The post-e407cb3 workspace had MACD parameters and scoring wired directly into `core/signal_engine.py`, plus plugin tests appended to `tests/unit/test_signal_engine.py`.

That mixed three boundaries:

```text
generic signal engine
strategy-specific MACD logic
plugin and envelope tests
```

## Decision

Use this boundary:

```text
core/signal_engine.py
  Generic signal engine, state machine, z-score/VWAP/ATR scoring.

utils/indicators.py
  Pure local indicator math, including ema_series() and macd().

core/macd_rebound_signal_plugin.py
  MACD strategy adapter. It owns MACD parameters, MACD confirmation, dry-run safety, and SignalEnvelope creation.

core/market_data_contract.py
  Local candle and batch data contracts.

core/signal_envelope.py
  Local dry-run signal output contract.
```

## Why Not Hard-Code MACD In SignalEngine

Hard-coding MACD in `SignalEngine` would make the base engine strategy-specific and would force global config keys such as `macd_fast`, `macd_slow`, and `macd_signal` into every run.

It would also make `tests/unit/test_signal_engine.py` depend on plugin contracts, which weakens module boundaries.

## Safety Properties

The plugin path:

```text
does not submit orders
does not call HTTP
does not read secrets
does not use testnet or live mode
requires dry_run=True
allows only paper/shadow/dry_run envelope modes
```

## Outcome

`core/signal_engine.py` was restored to generic behavior. `tests/unit/test_signal_engine.py` now tests only signal engine behavior. MACD-specific tests live in `tests/unit/test_macd_rebound_signal_plugin.py`.

This keeps the plugin suitable as an early foundation for a later Paper Trading Decision Engine without coupling strategy experiments into the core engine.
