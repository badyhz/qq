# Log Rotation Policy

## Retention Rules

| Artifact | Max Age | Max Count | Auto Cleanup | Safety Exception |
|----------|---------|-----------|--------------|------------------|
| e2e_run_output | 7d | 50 | No | No |
| shadow_signals | 3d | 30 | No | No |
| alert_events | 30d | 100 | No | No |
| operator_state | 7d | 50 | No | No |
| dashboard_html | 7d | 30 | No | No |
| safety_evidence | 365d | 1000 | No | Yes |
| scheduler_logs | 30d | 100 | No | No |
| testnet_simulation | 7d | 50 | No | No |

## Policy

- Auto cleanup is **disabled** by default.
- Safety evidence is **never** auto-deleted (safety_exception=True).
- Manual cleanup may be performed by operator after review.
- All retention rules are defined in `src/runtime_integrations/server/log_rotation_policy.py`.

## Commands

```bash
# View current retention rules
python3 -c "from src.runtime_integrations.server.log_rotation_policy import render_log_rotation_markdown; print(render_log_rotation_markdown())"

# Export rules as JSON
python3 -c "from src.runtime_integrations.server.log_rotation_policy import get_rules, write_rules; import pathlib; write_rules(get_rules(), pathlib.Path('data/runtime/hygiene/retention_rules.json'))"
```
