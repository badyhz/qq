# MACD Rebound Scanner External Integration

## Overview

Read-only integration wrapper for the existing MACD rebound scanner at `/www/wwwroot/quant_monitor/macd_rebound_scanner`. This integration does NOT rewrite the scanner — it adds health monitoring, log ingestion, reporting, and safety regression around the existing service.

## Modules

| Module | Purpose |
|--------|---------|
| `macd_rebound_config.py` | Config loader with path detection |
| `macd_rebound_health.py` | Directory structure health check |
| `macd_rebound_log_ingest.py` | Parse signals.csv, alerts.jsonl, scan_detail.jsonl, errors.log |
| `macd_rebound_daily_report.py` | Daily report combining health + logs |
| `macd_rebound_deployment_audit.py` | Deploy artifact verification |
| `macd_rebound_dry_run_plan.py` | 9-step dry-run execution plan |
| `macd_rebound_safety_regression.py` | Forbidden import/pattern scanner |

## Runners

```bash
python scripts/run_macd_rebound_external_health_check.py
python scripts/run_macd_rebound_log_ingest.py
python scripts/run_macd_rebound_daily_report.py
python scripts/run_macd_rebound_deployment_audit.py
python scripts/run_macd_rebound_dry_run_plan.py
python scripts/run_macd_rebound_integration_safety_regression.py
python scripts/run_macd_rebound_external_integration_suite.py
```

## Safety

- All modules end with `REAL_ORDER_SUBMIT_NOT_ALLOWED`
- Safety regression scans for forbidden imports (ccxt, requests, httpx, aiohttp, websocket)
- Safety regression scans for forbidden patterns (submit_order, cancel_order, etc.)
- Safety regression scans for real endpoint references
- Config defaults: `real_feishu_send_allowed: false`, `real_order_submit_allowed: false`

## Config

Edit `config/external_scanners/macd_rebound_scanner.example.yaml` to set `local_path_candidates` for your environment.

## Reports

All reports written to `reports/macd_rebound/` as JSON + markdown pairs.
