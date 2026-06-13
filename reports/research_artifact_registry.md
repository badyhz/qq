# Research Artifact Registry

**Total artifacts:** 11

## By Type

- **data_source_adapter:** 2
- **research_scanner:** 8
- **verification_report:** 1

## By Integration Target

- **alert_center:** 2
- **operator_console:** 1
- **strategy_registry:** 8

## Artifact Details

### docs/octopusycc_mouse_trade_plan_2026-05-23_2026-05-30.md

- **Type:** research_scanner
- **Category:** SAFE_RESEARCH
- **Reason:** Pure research notes on public X posts, no executable code, explicitly forbids live orders
- **Integration target:** strategy_registry
- **Network calls:** False
- **API keys:** False
- **Governance tracked:** True
- **Dry-run compatible:** True
- **Ready for integration:** True

### scripts/analyze_aleabitoreddit_watchlist.py

- **Type:** research_scanner
- **Category:** SAFE_RESEARCH
- **Reason:** Offline scanner, reads local exports only, never places orders
- **Integration target:** strategy_registry
- **Network calls:** False
- **API keys:** False
- **Governance tracked:** True
- **Dry-run compatible:** True
- **Ready for integration:** True

### scripts/run_right_breakout_scan_dry.py

- **Type:** research_scanner
- **Category:** SAFE_RESEARCH
- **Reason:** Mock connector, RuntimeError on submit, NoopExchange, pure dry signal scan
- **Integration target:** strategy_registry
- **Network calls:** False
- **API keys:** False
- **Governance tracked:** True
- **Dry-run compatible:** True
- **Ready for integration:** True

### scripts/run_shadow_observation_experiments.py

- **Type:** research_scanner
- **Category:** SAFE_RESEARCH
- **Reason:** Pure local kline cache computation, no network, no submit
- **Integration target:** strategy_registry
- **Network calls:** False
- **API keys:** False
- **Governance tracked:** True
- **Dry-run compatible:** True
- **Ready for integration:** True

### scripts/run_next_shadow_experiment_plan.py

- **Type:** research_scanner
- **Category:** SAFE_RESEARCH
- **Reason:** Offline signal scoring from cached klines, SHADOW_ONLY, NO_SUBMIT
- **Integration target:** strategy_registry
- **Network calls:** False
- **API keys:** False
- **Governance tracked:** True
- **Dry-run compatible:** True
- **Ready for integration:** True

### scripts/import_x_local_content.py

- **Type:** data_source_adapter
- **Category:** SAFE_IMPORTER
- **Reason:** Local file/clipboard import, no API, no network, subprocess only for pbpaste
- **Integration target:** alert_center
- **Network calls:** False
- **API keys:** False
- **Governance tracked:** True
- **Dry-run compatible:** True
- **Ready for integration:** True

### scripts/update_aleabitoreddit_market_data.py

- **Type:** data_source_adapter
- **Category:** SAFE_IMPORTER
- **Reason:** Fetches public OHLCV via yfinance, no API keys, no trading
- **Integration target:** alert_center
- **Network calls:** True
- **API keys:** False
- **Governance tracked:** True
- **Dry-run compatible:** False
- **Ready for integration:** True

### scripts/verify_risk_release_flow.py

- **Type:** verification_report
- **Category:** SAFE_REPORT
- **Reason:** Read-only verification, force-locks dry_run=True, outputs manual commands only
- **Integration target:** operator_console
- **Network calls:** False
- **API keys:** False
- **Governance tracked:** True
- **Dry-run compatible:** True
- **Ready for integration:** True

### tests/unit/test_analyze_aleabitoreddit_watchlist.py

- **Type:** research_scanner
- **Category:** SAFE_RESEARCH
- **Reason:** Pure unit tests for watchlist analysis, no network, no trading
- **Integration target:** strategy_registry
- **Network calls:** False
- **API keys:** False
- **Governance tracked:** True
- **Dry-run compatible:** True
- **Ready for integration:** True

### tests/unit/test_import_x_local_content.py

- **Type:** research_scanner
- **Category:** SAFE_RESEARCH
- **Reason:** Unit tests for local content import, subprocess only for local CLI
- **Integration target:** strategy_registry
- **Network calls:** False
- **API keys:** False
- **Governance tracked:** True
- **Dry-run compatible:** True
- **Ready for integration:** True

### tests/unit/test_update_aleabitoreddit_market_data.py

- **Type:** research_scanner
- **Category:** SAFE_RESEARCH
- **Reason:** Unit tests for market data updater with mock fetcher
- **Integration target:** strategy_registry
- **Network calls:** False
- **API keys:** False
- **Governance tracked:** True
- **Dry-run compatible:** True
- **Ready for integration:** True
