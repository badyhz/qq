# Paper Trading Ops

Long-running monitoring and strategy quality dashboard for the MACD rebound paper trading system.

## Modules

| Module | Purpose |
|--------|---------|
| `log_freshness_monitor.py` | Checks if scanner logs are still being produced |
| `paper_state_auditor.py` | Audits paper_positions.jsonl for health issues |
| `strategy_quality_metrics.py` | Computes win rate, expectancy, profit factor |
| `signal_quality_dashboard.py` | Grades signal-to-outcome pipeline A/B/C/D |
| `daily_ops_bundle.py` | Aggregates all reports into daily ops bundle |
| `scheduled_run_plan.py` | Generates cron/systemd templates (does not install) |
| `ops_alert_payload.py` | Generates dry-run alert payload |
| `ops_safety_regression.py` | Scans ops files for forbidden patterns |

## Runners

```bash
# Individual
python3 scripts/run_paper_ops_log_freshness.py
python3 scripts/run_paper_ops_state_audit.py
python3 scripts/run_paper_ops_strategy_metrics.py
python3 scripts/run_paper_ops_signal_dashboard.py
python3 scripts/run_paper_ops_daily_bundle.py
python3 scripts/run_paper_ops_alert_payload.py
python3 scripts/run_paper_ops_scheduled_plan.py
python3 scripts/run_paper_ops_safety_regression.py

# Full suite
python3 scripts/run_paper_ops_suite.py
```

## Strategy Quality Grades

| Grade | Criteria |
|-------|----------|
| A | expectancy > 0.5R, win_rate >= 50%, 20+ closed trades |
| B | expectancy > 0R, win_rate >= 40%, 20+ closed trades |
| C | expectancy > -0.1R, 20+ closed trades |
| D | expectancy <= -0.1R |
| INSUFFICIENT_DATA | < 20 closed trades |

## Daily Bundle Status

- **HEALTHY**: No critical alerts or warnings
- **WARNING**: Stale logs, weak strategy, or marginal grade
- **CRITICAL**: Log failures, audit failures, or negative edge

## Safety

All outputs are dry-run only. No real orders, no real sends, no credential reads.
Safety regression scans all ops files for forbidden imports and patterns.
