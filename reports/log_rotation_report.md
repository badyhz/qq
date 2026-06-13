# Log Rotation Policy

| Artifact | Max Age | Max Count | Auto Cleanup | Safety Exception |
|----------|---------|-----------|--------------|------------------|
| e2e_run_output | 7d | 50 | False | False |
| shadow_signals | 3d | 30 | False | False |
| alert_events | 30d | 100 | False | False |
| operator_state | 7d | 50 | False | False |
| dashboard_html | 7d | 30 | False | False |
| safety_evidence | 365d | 1000 | False | True |
| scheduler_logs | 30d | 100 | False | False |
| testnet_simulation | 7d | 50 | False | False |

**Note:** Auto cleanup is disabled by default. Safety evidence is never auto-deleted.
