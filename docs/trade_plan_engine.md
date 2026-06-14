# Trade Plan Engine

## Overview

Generates trade plans and paper position lifecycle for MACD rebound signals. Dry-run only — no real orders, no real Feishu sends.

## Signal Flow

```
signals.csv / alerts.jsonl
  → SignalAdapter (deduplicate, validate)
  → EntryPlan (entry zone, confidence)
  → RiskPlan (position sizing, risk level)
  → ExitPlan (SL, TP1/TP2/TP3, time stop)
  → TradePlan (combined)
  → PaperPosition (lifecycle simulation)
  → ReplayEvaluator (win rate, expectancy)
  → FeishuPayload (dry-run alert)
  → DailyReview (summary report)
```

## Modules

| Module | Purpose |
|--------|---------|
| `models.py` | SignalCandidate, TradePlan, RiskPlan, ExitPlan, PaperPosition |
| `signal_adapter.py` | Read scanner outputs → SignalCandidate |
| `entry_plan.py` | Entry zone, type, confidence |
| `risk_plan.py` | Position sizing, risk level |
| `exit_plan.py` | SL/TP calculation, exit rules |
| `paper_position.py` | Create PaperPosition from TradePlan |
| `paper_lifecycle.py` | Simulate entry/exit with OHLCV data |
| `replay_evaluator.py` | Win rate, expectancy, PnL stats |
| `feishu_trade_plan_payload.py` | Dry-run Feishu alert payload |
| `daily_trade_plan_review.py` | Daily summary report |
| `trade_plan_safety_regression.py` | Forbidden pattern scanner |

## Runners

```bash
python3 scripts/run_macd_rebound_signal_to_trade_plan.py
python3 scripts/run_trade_plan_risk_preview.py
python3 scripts/run_paper_position_lifecycle.py
python3 scripts/run_trade_plan_replay_evaluator.py
python3 scripts/run_feishu_trade_plan_payload_dry_run.py
python3 scripts/run_daily_trade_plan_review.py
python3 scripts/run_trade_plan_engine_safety_regression.py
python3 scripts/run_trade_plan_engine_suite.py
```

## Safety

- All TradePlan.dry_run_only = True
- All PaperPosition.dry_run_only = True
- All FeishuPayload.dry_run_only = True
- Safety regression scans for forbidden imports/patterns
- No real credentials, no real endpoints, no real sends

## Default Parameters

| Parameter | Value |
|-----------|-------|
| account_equity_placeholder | 10000 |
| risk_per_trade_pct | 0.5% |
| max_account_risk_pct | 1.0% |
| stop_loss | price * 0.97 or ma25 * 0.995 |
| TP1 | 1.5R |
| TP2 | 2.5R |
| TP3 | 4R |
| max_hold_bars | 48 |
