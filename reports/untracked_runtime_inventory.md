# Untracked Runtime Inventory

**Total files:** 29
**High-risk files:** 10

## Risk Category Summary

- **HIGH_RISK_FLATTEN:** 1
- **HIGH_RISK_LIVE_RUNTIME:** 1
- **HIGH_RISK_TESTNET_SUBMIT:** 8
- **NEEDS_HUMAN_REVIEW:** 2
- **SAFE_IMPORTER:** 2
- **SAFE_REPORT:** 1
- **SAFE_RESEARCH:** 8
- **SHADOW_PIPELINE:** 4
- **TESTNET_DRY_RUN_ONLY:** 2

## Inventory Details

### 🟡 core/live_runner.py

- **Risk category:** NEEDS_HUMAN_REVIEW
- **Reason:** Orchestration gateway: delegates to execution_engine, has run_testnet_order_smoke with order params; safe only if engine is noop
- **Network calls:** False
- **API keys:** False
- **Order submit:** True
- **Exchange adapter:** False
- **Recommendation:** Queue for human review before any integration

### 🟢 docs/octopusycc_mouse_trade_plan_2026-05-23_2026-05-30.md

- **Risk category:** SAFE_RESEARCH
- **Reason:** Pure research notes on public X posts, no executable code, explicitly forbids live orders
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Integrate into strategy registry as research artifact

### 🟢 scripts/analyze_aleabitoreddit_watchlist.py

- **Risk category:** SAFE_RESEARCH
- **Reason:** Offline scanner, reads local exports only, never places orders
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Integrate into strategy registry as research artifact

### 🟢 scripts/run_right_breakout_scan_dry.py

- **Risk category:** SAFE_RESEARCH
- **Reason:** Mock connector, RuntimeError on submit, NoopExchange, pure dry signal scan
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Integrate into strategy registry as research artifact

### 🟢 scripts/run_shadow_observation_experiments.py

- **Risk category:** SAFE_RESEARCH
- **Reason:** Pure local kline cache computation, no network, no submit
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Integrate into strategy registry as research artifact

### 🟢 scripts/run_next_shadow_experiment_plan.py

- **Risk category:** SAFE_RESEARCH
- **Reason:** Offline signal scoring from cached klines, SHADOW_ONLY, NO_SUBMIT
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Integrate into strategy registry as research artifact

### 🟢 scripts/import_x_local_content.py

- **Risk category:** SAFE_IMPORTER
- **Reason:** Local file/clipboard import, no API, no network, subprocess only for pbpaste
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Integrate into alert center as data source adapter

### 🟢 scripts/update_aleabitoreddit_market_data.py

- **Risk category:** SAFE_IMPORTER
- **Reason:** Fetches public OHLCV via yfinance, no API keys, no trading
- **Network calls:** True
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Integrate into alert center as data source adapter

### 🟢 scripts/verify_risk_release_flow.py

- **Risk category:** SAFE_REPORT
- **Reason:** Read-only verification, force-locks dry_run=True, outputs manual commands only
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Integrate into operator console as report generator

### 🟢 scripts/run_daily_shadow_scan_pipeline.py

- **Risk category:** SHADOW_PIPELINE
- **Reason:** Shadow pipeline orchestrator, all steps shadow/observation, no submit
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Connect to shadow pipeline registry and operator console

### 🟢 scripts/run_shadow_sample_collection_pipeline.py

- **Risk category:** SHADOW_PIPELINE
- **Reason:** Shadow sample collection orchestrator, kline backfill forced dry_run=True
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Connect to shadow pipeline registry and operator console

### 🟢 scripts/run_shadow_universe_collector.py

- **Risk category:** SHADOW_PIPELINE
- **Reason:** Shadow universe collector, NO_TESTNET_SUBMIT, cached klines only
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Connect to shadow pipeline registry and operator console

### 🟢 scripts/run_right_breakout_param_observation.py

- **Risk category:** SHADOW_PIPELINE
- **Reason:** Public market data + signal eval, enable_live_trading=False, dormant submit path
- **Network calls:** True
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Connect to shadow pipeline registry and operator console

### 🟢 scripts/replay_shadow_order_plans_as_testnet_dry.py

- **Risk category:** TESTNET_DRY_RUN_ONLY
- **Reason:** Public exchange info call, submit path explicitly stubbed out, writes dry-run payloads
- **Network calls:** True
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Wrap in dry-run adapter for testnet simulation framework

### 🟢 scripts/verify_testnet_repair_scenarios.py

- **Risk category:** TESTNET_DRY_RUN_ONLY
- **Reason:** Read-only testnet diagnostic, force-locks dry_run=True, produces repair plans
- **Network calls:** True
- **API keys:** True
- **Order submit:** False
- **Exchange adapter:** True
- **Recommendation:** Wrap in dry-run adapter for testnet simulation framework

### 🔴 scripts/run_controlled_testnet_shift.py

- **Risk category:** HIGH_RISK_TESTNET_SUBMIT
- **Reason:** Generates submit_approved_candidates.py commands, calls testnet API, orchestrates full pipeline
- **Network calls:** True
- **API keys:** False
- **Order submit:** True
- **Exchange adapter:** False
- **Recommendation:** ISOLATE: Add to denylist, require human approval before any execution

### 🔴 scripts/run_observation_shift_runtime.py

- **Risk category:** HIGH_RISK_TESTNET_SUBMIT
- **Reason:** Queries live testnet state via API, argparse self-labels HIGH_RISK
- **Network calls:** True
- **API keys:** True
- **Order submit:** False
- **Exchange adapter:** True
- **Recommendation:** ISOLATE: Add to denylist, require human approval before any execution

### 🔴 scripts/run_replay_submit_batch.py

- **Risk category:** HIGH_RISK_TESTNET_SUBMIT
- **Reason:** Submits orders to testnet via submit_replayed_testnet_payloads
- **Network calls:** True
- **API keys:** False
- **Order submit:** True
- **Exchange adapter:** True
- **Recommendation:** ISOLATE: Add to denylist, require human approval before any execution

### 🔴 scripts/run_signal_testnet_trial.py

- **Risk category:** HIGH_RISK_TESTNET_SUBMIT
- **Reason:** Creates real Binance testnet connector, --submit-testnet flag enables order submit
- **Network calls:** True
- **API keys:** True
- **Order submit:** True
- **Exchange adapter:** True
- **Recommendation:** ISOLATE: Add to denylist, require human approval before any execution

### 🔴 scripts/run_spot_testnet_acceptance.py

- **Risk category:** HIGH_RISK_TESTNET_SUBMIT
- **Reason:** Full testnet acceptance: submit order, query status, cancel order
- **Network calls:** True
- **API keys:** True
- **Order submit:** True
- **Exchange adapter:** True
- **Recommendation:** ISOLATE: Add to denylist, require human approval before any execution

### 🔴 scripts/run_testnet_order_smoke.py

- **Risk category:** HIGH_RISK_TESTNET_SUBMIT
- **Reason:** Testnet smoke test with real order submit, accepts --mode live
- **Network calls:** True
- **API keys:** True
- **Order submit:** True
- **Exchange adapter:** True
- **Recommendation:** ISOLATE: Add to denylist, require human approval before any execution

### 🔴 scripts/submit_approved_candidates.py

- **Risk category:** HIGH_RISK_TESTNET_SUBMIT
- **Reason:** Main approved-candidate-to-order bridge, delegates to run_replay_submit_batch
- **Network calls:** True
- **API keys:** False
- **Order submit:** True
- **Exchange adapter:** True
- **Recommendation:** ISOLATE: Add to denylist, require human approval before any execution

### 🔴 scripts/submit_replayed_testnet_payload.py

- **Risk category:** HIGH_RISK_TESTNET_SUBMIT
- **Reason:** Core order submission engine, submits entry+SL+TP to Binance testnet
- **Network calls:** True
- **API keys:** True
- **Order submit:** True
- **Exchange adapter:** True
- **Recommendation:** ISOLATE: Add to denylist, require human approval before any execution

### 🔴 scripts/live_playbook.py

- **Risk category:** HIGH_RISK_LIVE_RUNTIME
- **Reason:** Accepts --mode live, imports ExecutionEngine+OrderManager, enable_live_trading=True
- **Network calls:** False
- **API keys:** False
- **Order submit:** True
- **Exchange adapter:** True
- **Recommendation:** ISOLATE: Add to denylist, require human approval before any execution

### 🔴 scripts/safe_flatten_testnet_symbol.py

- **Risk category:** HIGH_RISK_FLATTEN
- **Reason:** Submits MARKET reduce-only orders + cancels algo orders on testnet, reads API keys
- **Network calls:** True
- **API keys:** True
- **Order submit:** True
- **Exchange adapter:** True
- **Recommendation:** ISOLATE: Add to denylist, require human approval before any execution

### 🟡 scripts/run_remediation_shadow_only_loop.py

- **Risk category:** NEEDS_HUMAN_REVIEW
- **Reason:** Executes arbitrary shell commands via subprocess.run(shell=True), command injection surface
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Queue for human review before any integration

### 🟢 tests/unit/test_analyze_aleabitoreddit_watchlist.py

- **Risk category:** SAFE_RESEARCH
- **Reason:** Pure unit tests for watchlist analysis, no network, no trading
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Integrate into strategy registry as research artifact

### 🟢 tests/unit/test_import_x_local_content.py

- **Risk category:** SAFE_RESEARCH
- **Reason:** Unit tests for local content import, subprocess only for local CLI
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Integrate into strategy registry as research artifact

### 🟢 tests/unit/test_update_aleabitoreddit_market_data.py

- **Risk category:** SAFE_RESEARCH
- **Reason:** Unit tests for market data updater with mock fetcher
- **Network calls:** False
- **API keys:** False
- **Order submit:** False
- **Exchange adapter:** False
- **Recommendation:** Integrate into strategy registry as research artifact
