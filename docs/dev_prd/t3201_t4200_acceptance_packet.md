# T3201-T4200 Acceptance Packet

## Acceptance Criteria

### Module Importability
All core modules must be importable without error:
- `core.historical_ohlcv_schema`
- `core.historical_ohlcv_chunked_reader`
- `core.walk_forward_split_engine`
- `core.offline_breakout_signal_engine`
- `core.offline_backtest_trade_simulator`
- `core.offline_backtest_metrics_engine`
- `core.offline_shadow_metric_engine`
- `core.offline_shadow_scorecard`
- `core.offline_shadow_comparison`
- `core.offline_shadow_report_renderer`
- `core.offline_shadow_bundle_builder`
- `core.offline_shadow_parameter_set`
- `core.offline_backtest_orchestrator`

### Fixture Integrity
- `tests/fixtures/historical_ohlcv/BTCUSDT_5m.csv` exists and is valid CSV
- `tests/fixtures/historical_ohlcv/ETHUSDT_5m.csv` exists and is valid CSV
- `tests/fixtures/offline_shadow_research/` contains all expected JSON fixtures

### Functional Tests
- Walk-forward split produces correct train/test ranges on fixtures
- Parameter grid produces expected presets
- Signal engine produces signals on fixture data
- Trade simulation produces valid outcomes
- Metrics computation produces correct values
- Scorecard grading produces PASS/WATCH/REJECT
- Comparison compares experiments correctly
- Report renderers produce non-empty output
- Bundle builder produces manifest with correct safety flags
- Pipeline orchestrator runs end-to-end on fixtures

### Test Coverage
- `tests/unit/test_historical_backtest_acceptance.py`: 20+ tests
- `tests/unit/test_verify_historical_backtest_lab.py`: 8+ tests

## Verification Commands

```bash
# Run all acceptance tests
python3 -m pytest tests/unit/test_historical_backtest_acceptance.py -v

# Run verification script
python3 scripts/verify_historical_backtest_lab.py

# Run verification tests
python3 -m pytest tests/unit/test_verify_historical_backtest_lab.py -v

# Run all backtest-related tests
python3 -m pytest tests/unit/test_historical_ohlcv_schema.py tests/unit/test_walk_forward_split_engine.py tests/unit/test_offline_shadow_scorecard.py tests/unit/test_offline_shadow_metric_engine.py tests/unit/test_offline_shadow_bundle_builder.py tests/unit/test_offline_shadow_comparison.py tests/unit/test_offline_shadow_report_renderer.py tests/unit/test_historical_backtest_acceptance.py tests/unit/test_verify_historical_backtest_lab.py -v
```

## Safety Boundary Confirmation

- All modules are pure functions or frozen dataclasses
- No network calls in any module
- No exchange client usage
- No credential access
- release_hold = "HOLD" always
- No live trading authorization
