# Shadow Pipeline Registry

**Total pipeline scripts:** 4

## Pipeline Stage Order

1. **stage_0_orchestration** (orchestrator): `scripts/run_daily_shadow_scan_pipeline.py`
1. **stage_1_backfill** (sample_collector): `scripts/run_shadow_sample_collection_pipeline.py`
1. **stage_2_universe** (universe_collector): `scripts/run_shadow_universe_collector.py`
1. **stage_3_signal_eval** (signal_evaluator): `scripts/run_right_breakout_param_observation.py`

## Registry Details

### scripts/run_daily_shadow_scan_pipeline.py

- **Role:** orchestrator
- **Stage:** stage_0_orchestration
- **Risk reason:** Shadow pipeline orchestrator, all steps shadow/observation, no submit
- **Network calls:** False
- **Shadow only:** True
- **No submit:** True
- **Governance tracked:** True
- **Operator console connected:** True

### scripts/run_shadow_sample_collection_pipeline.py

- **Role:** sample_collector
- **Stage:** stage_1_backfill
- **Risk reason:** Shadow sample collection orchestrator, kline backfill forced dry_run=True
- **Network calls:** False
- **Shadow only:** True
- **No submit:** True
- **Governance tracked:** True
- **Operator console connected:** True

### scripts/run_shadow_universe_collector.py

- **Role:** universe_collector
- **Stage:** stage_2_universe
- **Risk reason:** Shadow universe collector, NO_TESTNET_SUBMIT, cached klines only
- **Network calls:** False
- **Shadow only:** True
- **No submit:** True
- **Governance tracked:** True
- **Operator console connected:** True

### scripts/run_right_breakout_param_observation.py

- **Role:** signal_evaluator
- **Stage:** stage_3_signal_eval
- **Risk reason:** Public market data + signal eval, enable_live_trading=False, dormant submit path
- **Network calls:** True
- **Shadow only:** True
- **No submit:** True
- **Governance tracked:** True
- **Operator console connected:** True
