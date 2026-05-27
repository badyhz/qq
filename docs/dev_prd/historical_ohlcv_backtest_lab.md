# Historical OHLCV Backtest Lab — Architecture Overview

## Module Map

```
core/
├── historical_ohlcv_schema.py          # Frozen dataclasses: HistoricalBar, IssueType, QualityReport
├── historical_ohlcv_chunked_reader.py  # Chunked CSV reader, gap detection, dedup
├── walk_forward_split_engine.py        # Rolling/expanding train/test splits
├── offline_breakout_signal_engine.py   # Breakout signal scanner
├── offline_backtest_trade_simulator.py # Trade simulation with slippage/fees
├── offline_backtest_metrics_engine.py  # Per-run and aggregate metrics
├── offline_shadow_metric_engine.py     # Shadow metric computation
├── offline_shadow_scorecard.py         # PASS/WATCH/REJECT grading
├── offline_shadow_comparison.py        # Multi-experiment comparison
├── offline_shadow_report_renderer.py   # Markdown/JSON/HTML report output
├── offline_shadow_bundle_builder.py    # Artifact bundle assembly + SHA256
├── offline_shadow_parameter_set.py     # Parameter grid presets
└── offline_backtest_orchestrator.py    # Pipeline coordinator
```

## Data Flow

```
CSV File
    │
    ▼
┌─────────────────────────┐
│  Chunked Reader         │  Reads CSV in fixed-size chunks
│  (historical_ohlcv_     │  Never loads full file into memory
│   chunked_reader.py)    │
└────────┬────────────────┘
         │ List[HistoricalBar]
         ▼
┌─────────────────────────┐
│  Walk-Forward Split     │  Generates train/test index ranges
│  (walk_forward_split_   │  Rolling or expanding window
│   engine.py)            │
└────────┬────────────────┘
         │ List[WalkForwardSplit]
         ▼
┌─────────────────────────┐
│  Breakout Signal Engine │  Scans bars for breakout patterns
│  (offline_breakout_     │  Returns List[BreakoutSignal]
│   signal_engine.py)     │
└────────┬────────────────┘
         │ List[BreakoutSignal]
         ▼
┌─────────────────────────┐
│  Trade Simulator        │  Simulates entry/exit with slippage
│  (offline_backtest_     │  Returns List[TradeOutcome]
│   trade_simulator.py)   │
└────────┬────────────────┘
         │ List[TradeOutcome]
         ▼
┌─────────────────────────┐
│  Metrics Engine         │  Computes win_rate, expectancy, PF, etc.
│  (offline_backtest_     │  Per-run and aggregate metrics
│   metrics_engine.py)    │
└────────┬────────────────┘
         │ Dict metrics
         ▼
┌─────────────────────────┐
│  Scorecard              │  PASS / WATCH / REJECT grading
│  (offline_shadow_       │  Quality gates and reason codes
│   scorecard.py)         │
└────────┬────────────────┘
         │ Dict scorecard
         ▼
┌─────────────────────────┐
│  Bundle Builder         │  Assembles artifacts + SHA256 manifest
│  (offline_shadow_       │  Safety flags: release_hold=HOLD
│   bundle_builder.py)    │
└─────────────────────────┘
```

## Safety Invariants

1. **release_hold = "HOLD"** — Always. No exceptions.
2. **No network calls** — All functions are pure or file-I/O only.
3. **No live trading** — No exchange clients, no order submission.
4. **No secrets** — No credentials, API keys, or tokens.
5. **Frozen dataclasses** — All core models are immutable.
6. **Explicit git add** — No `git add .` permitted.

## CLI Usage

```bash
# Run full backtest on fixture data
python3 -m core.offline_backtest_orchestrator

# Run acceptance tests
python3 -m pytest tests/unit/test_historical_backtest_acceptance.py -v

# Run verification script
python3 scripts/verify_historical_backtest_lab.py
```

## Test Coverage

- Schema validation: 24 tests
- Chunked reader: 15+ tests
- Walk-forward splits: 22 tests
- Trade simulator: 12+ tests
- Metrics engine: 18+ tests
- Scorecard grading: 10+ tests
- Bundle builder: 8+ tests
- Comparison: 6+ tests
- Report renderers: 10+ tests
- Acceptance: 20+ tests
- Verification: 8+ tests

Total: 150+ tests across the backtest lab.
