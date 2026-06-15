# Next Staging Plan After e407cb3

**Date:** 2026-06-16
**Status:** PREVIEW ONLY - do not execute without human authorization

## Batch 2A - MACD Plugin Runtime Closure

The MACD plugin now depends on `utils/indicators.py::macd()`, so the runtime closure is the 5 MACD files plus the indicator helper.

Preview only:

```bash
git add \
  utils/indicators.py \
  core/market_data_contract.py \
  core/signal_envelope.py \
  core/macd_rebound_signal_plugin.py \
  tests/unit/test_market_data_contract.py \
  tests/unit/test_macd_rebound_signal_plugin.py
```

Why:

```text
local contracts
dry-run signal envelope
MACD strategy plugin
unit tests for plugin and data contract
pure indicator math dependency
```

## Batch 2B - Dry-Run Config And Generic Signal Test

Preview only:

```bash
git add \
  config.yaml \
  tests/unit/test_signal_engine.py
```

Why:

```text
dry_run_slippage_rate realism setting
generic SignalEngine full short signal path test
```

## HOLD - Order Manager

Do not stage yet:

```text
core/order_manager.py
```

Reason: the current diff changes live-mode update behavior and adds live `TIME_EXIT` handling. That is outside the dry-run MACD plugin consolidation scope.

## HOLD - Unrelated Untracked Files

Do not stage:

```text
1700+ unrelated untracked files
.mcp.json
relay/
research/
safety / ultimate / final / absolute generated modules
testnet / live / deploy / push / remote / release files
```

## Suggested Verification Before Any Future Staging

```bash
python3 -m compileall -q core/signal_engine.py utils/indicators.py core/market_data_contract.py core/signal_envelope.py core/macd_rebound_signal_plugin.py
.venv/bin/pytest -q tests/unit/test_signal_engine.py tests/unit/test_market_data_contract.py tests/unit/test_macd_rebound_signal_plugin.py
git diff --cached --name-only
```

Expected:

```text
compileall PASS
pytest PASS
git diff --cached --name-only empty before staging
```
