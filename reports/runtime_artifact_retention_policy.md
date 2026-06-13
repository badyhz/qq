# Artifact Retention Policy

| Pattern | Retention | Max Count | Auto Cleanup |
|---------|-----------|-----------|--------------|
| data/runtime/e2e/run_manifest.json | 30d | 100 | False |
| data/runtime/shadow/signals.jsonl | 7d | 50 | False |
| data/runtime/alerts/alerts.jsonl | 30d | 100 | False |
| data/runtime/operator/system_state.json | 30d | 100 | False |
| reports/operator_dashboard.html | 7d | 30 | False |
| reports/system_dry_run_e2e_report.md | 30d | 100 | False |

**Note:** Auto cleanup is disabled. Artifacts must be manually reviewed before deletion.
