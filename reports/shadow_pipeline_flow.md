# Shadow Pipeline Flow

```
├── [stage_0_orchestration] orchestrator
│   └── scripts/run_daily_shadow_scan_pipeline.py
├── [stage_1_backfill] sample_collector
│   └── scripts/run_shadow_sample_collection_pipeline.py
├── [stage_2_universe] universe_collector
│   └── scripts/run_shadow_universe_collector.py
└── [stage_3_signal_eval] signal_evaluator
│   └── scripts/run_right_breakout_param_observation.py
```
