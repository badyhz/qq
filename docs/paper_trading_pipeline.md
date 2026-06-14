# Paper Trading Pipeline

## Overview

Connects `macd_rebound_scanner` real log outputs to trade plan generation, paper position lifecycle tracking, and daily review. Dry-run only — no real orders, no real Feishu sends.

## Pipeline Flow

```
scanner signals.csv / alerts.jsonl
  → ScannerLogSource (read + validate)
  → SignalDeduplicator (exact dedup + cooldown filter)
  → TradePlanBatchBuilder (generate plans via trade_plan_engine)
  → PaperPositionStore (append new positions to JSONL)
  → PaperPositionUpdater (simulate TP/STOP/TIME_STOP)
  → PaperReplayScheduler (identify what needs updating)
  → DailyPaperReview (aggregate stats)
  → FeishuPaperReviewPayload (dry-run alert)
```

## Modules

| Module | Purpose |
|--------|---------|
| `models.py` | All pipeline data models |
| `scanner_log_source.py` | Read scanner CSV/JSONL/log files |
| `signal_deduplicator.py` | Exact + cooldown dedup |
| `trade_plan_batch_builder.py` | Generate TradePlans from signals |
| `paper_position_store.py` | Local JSONL state file |
| `paper_position_updater.py` | Simulate TP/STOP/TIME_STOP |
| `paper_replay_scheduler.py` | Identify positions needing update |
| `daily_paper_review.py` | Aggregate daily stats |
| `feishu_paper_review_payload.py` | Dry-run Feishu payload |
| `pipeline_safety_regression.py` | Forbidden pattern scanner |

## Runners

```bash
PYTHONPATH=. python3 scripts/run_paper_trading_pipeline_suite.py
PYTHONPATH=. python3 scripts/run_daily_paper_trading_review.py
PYTHONPATH=. python3 scripts/run_feishu_paper_review_payload_dry_run.py
```

## Safety

- All PaperPositionRecord.dry_run_only = True
- All FeishuPayload.dry_run_only = True
- No real credentials read
- No real Feishu sends
- No real orders

## Paper Position Store

Positions stored at `data/runtime/paper_trading_pipeline/paper_positions.jsonl` (not committed).

## Daily Review Metrics

- raw_signals / deduped_signals
- trade_plans_created / rejected
- paper_open / paper_closed / tp_hit / stop
- win_rate_placeholder
- top_symbols / risk_notes / next_actions
