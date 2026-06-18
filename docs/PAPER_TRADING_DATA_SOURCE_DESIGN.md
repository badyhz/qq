# Paper Trading Data Source Design — Round 9

**Date:** 2026-06-16
**Status:** ROUND9_READONLY_DATA_SOURCE_READY

## Summary

Round 9 adds a readonly data source abstraction layer to the paper trading system.

The system can now switch between fixture data and snapshot data via config.
Snapshot adapter is skeleton only — no real network, no real HTTP.

## Architecture

### Data Source Interface

`core/paper_trading/data_source.py` defines:

- `MarketBar` — readonly K-line bar
- `MarketSnapshot` — readonly point-in-time snapshot
- `DataSourceConfig` — readonly configuration
- `DataSource` — abstract base class
- `create_data_source()` — factory function

### Implementations

- `FixtureDataSource` — loads from local JSON fixtures
- `SnapshotAdapter` — skeleton only, returns empty/sample data

### Data Flow

```
DataSourceConfig (mode: fixture / snapshot)
  → create_data_source(config)
    → FixtureDataSource 或 SnapshotAdapter
      → adapter.get_bars(symbol, timeframe, limit)
        → signal_adapter.macd_rebound_signal()
          → order_plan.create_plan()
            → paper runtime
```

## Safety

### What is allowed

- Fixture data source (local JSON)
- Snapshot adapter skeleton (no network)
- Config switch between fixture/snapshot

### What is forbidden

- NO websocket
- NO account sync
- NO API key
- NO .env read
- NO requests/httpx/aiohttp
- NO order
- NO testnet
- NO live
- NO secret
- NO real HTTP

### Verification

- `test_paper_data_source_safety.py` — AST checks for forbidden imports
- `run_paper_data_source_smoke.py` — runtime safety verification
- Acceptance suite — data source existence and safety checks

## Files Added

| File | Purpose |
|------|---------|
| `core/paper_trading/data_source.py` | Interface and models |
| `core/paper_trading/fixture_adapter.py` | Fixture data source |
| `core/paper_trading/snapshot_adapter.py` | Snapshot skeleton |
| `tests/unit/test_paper_data_source.py` | Interface tests |
| `tests/unit/test_paper_fixture_adapter.py` | Fixture adapter tests |
| `tests/unit/test_paper_snapshot_adapter.py` | Snapshot adapter tests |
| `tests/unit/test_paper_data_source_safety.py` | Safety tests |
| `scripts/run_paper_data_source_smoke.py` | Smoke test |

## Files Modified

| File | Change |
|------|--------|
| `core/paper_trading/runtime_config.py` | Added `data_source_mode` field |
| `scripts/run_paper_trading_acceptance_suite.py` | Updated data source checks |

## Known Limits

- Snapshot adapter is skeleton only — no real market data
- No websocket — real-time data not supported
- No account/order integration — data source is readonly
- Phase 10 Shadow Gate must be defined after Round 9

## Next Steps

- Phase 10: Real market paper shadow (requires separate human approval)
- Phase 10 will add real market data via public REST (if approved)
- PHASE10_SHADOW_GATE.md will be created after Phase 10 approval
