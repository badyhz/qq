# Strategy Registry Overview

**Total strategies:** 11
**All IDs unique:** True

## Promotion Status Summary

- **RESEARCH_ONLY:** 4
- **SHADOW_CANDIDATE:** 1
- **WATCHLIST_ONLY:** 6

## Strategy Details

### macd_momentum_v1

- **Name:** MACD Second Momentum Strategy
- **Market:** crypto
- **Asset type:** spot
- **Signal type:** macd_crossover
- **Timeframe:** 4h
- **Risk level:** MEDIUM
- **Current mode:** SHADOW_ONLY
- **Promotion status:** RESEARCH_ONLY
- **Test status:** PENDING
- **Next action:** COLLECT_SHADOW_EVIDENCE
- **Blockers:** needs_shadow_evidence, needs_backtest_validation

### institutional_rally_model_1

- **Name:** Institutional Rally Model 1
- **Market:** us_stock
- **Asset type:** equity
- **Signal type:** volume_price_breakout
- **Timeframe:** daily
- **Risk level:** MEDIUM
- **Current mode:** SHADOW_ONLY
- **Promotion status:** WATCHLIST_ONLY
- **Test status:** PENDING
- **Next action:** VALIDATE_DATA_SOURCE
- **Blockers:** needs_live_data_validation

### institutional_rally_model_2

- **Name:** Institutional Rally Model 2
- **Market:** us_stock
- **Asset type:** equity
- **Signal type:** earnings_momentum
- **Timeframe:** daily
- **Risk level:** MEDIUM
- **Current mode:** SHADOW_ONLY
- **Promotion status:** WATCHLIST_ONLY
- **Test status:** PENDING
- **Next action:** BUILD_DATA_PIPELINE
- **Blockers:** needs_earnings_data_pipeline

### institutional_rally_model_3

- **Name:** Institutional Rally Model 3
- **Market:** us_stock
- **Asset type:** equity
- **Signal type:** sector_rotation
- **Timeframe:** weekly
- **Risk level:** LOW
- **Current mode:** SHADOW_ONLY
- **Promotion status:** RESEARCH_ONLY
- **Test status:** PENDING
- **Next action:** COLLECT_SECTOR_DATA
- **Blockers:** needs_sector_data

### ai_infra_watchlist

- **Name:** AI Infrastructure Watchlist
- **Market:** us_stock
- **Asset type:** equity
- **Signal type:** thematic_watchlist
- **Timeframe:** daily
- **Risk level:** LOW
- **Current mode:** SHADOW_ONLY
- **Promotion status:** WATCHLIST_ONLY
- **Test status:** PENDING
- **Next action:** MONITOR

### cpo_watchlist

- **Name:** CPO Watchlist
- **Market:** us_stock
- **Asset type:** equity
- **Signal type:** thematic_watchlist
- **Timeframe:** daily
- **Risk level:** LOW
- **Current mode:** SHADOW_ONLY
- **Promotion status:** WATCHLIST_ONLY
- **Test status:** PENDING
- **Next action:** MONITOR

### silicon_photonics_watchlist

- **Name:** Silicon Photonics Watchlist
- **Market:** us_stock
- **Asset type:** equity
- **Signal type:** thematic_watchlist
- **Timeframe:** daily
- **Risk level:** LOW
- **Current mode:** SHADOW_ONLY
- **Promotion status:** WATCHLIST_ONLY
- **Test status:** PENDING
- **Next action:** MONITOR

### earnings_event_strategy

- **Name:** Earnings Event Strategy
- **Market:** us_stock
- **Asset type:** equity
- **Signal type:** earnings_surprise
- **Timeframe:** event
- **Risk level:** HIGH
- **Current mode:** SHADOW_ONLY
- **Promotion status:** RESEARCH_ONLY
- **Test status:** PENDING
- **Next action:** BUILD_EARNINGS_PIPELINE
- **Blockers:** needs_earnings_data_pipeline, needs_event_backtest

### stock_price_alert_watcher

- **Name:** Stock Price Alert Watcher
- **Market:** us_stock
- **Asset type:** equity
- **Signal type:** price_alert
- **Timeframe:** intraday
- **Risk level:** LOW
- **Current mode:** SHADOW_ONLY
- **Promotion status:** WATCHLIST_ONLY
- **Test status:** PENDING
- **Next action:** MONITOR

### binance_futures_scanner

- **Name:** Binance Futures Scanner
- **Market:** crypto
- **Asset type:** futures
- **Signal type:** volume_breakout
- **Timeframe:** 1h
- **Risk level:** HIGH
- **Current mode:** SHADOW_ONLY
- **Promotion status:** SHADOW_CANDIDATE
- **Test status:** PENDING
- **Next action:** COLLECT_SHADOW_EVIDENCE
- **Blockers:** needs_shadow_evidence, needs_risk_validation

### options_call_strategy

- **Name:** Options Call Trading Plan
- **Market:** us_stock
- **Asset type:** options
- **Signal type:** volatility_play
- **Timeframe:** weekly
- **Risk level:** HIGH
- **Current mode:** SHADOW_ONLY
- **Promotion status:** RESEARCH_ONLY
- **Test status:** PENDING
- **Next action:** RESEARCH_OPTIONS_DATA
- **Blockers:** needs_options_data_source, needs_greeks_model

---
REGISTRY ONLY. NO REAL TRADING AUTHORIZED.
