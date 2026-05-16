# Scheduled Observation

`scripts/run_scheduled_observation.py` runs one testnet observation duty cycle for cron or launchd. It is not a daemon and does not submit orders, cancel orders, flatten positions, send real notifications, or support live execution.

Example cron entry:

```cron
*/15 * * * * cd /Users/winnie/Documents/trae_projects/qq && PYTHONPATH=. ./.venv/bin/python scripts/run_scheduled_observation.py --env testnet --symbols FETUSDT,OPUSDT --dry-run
```

Example launchd `ProgramArguments`:

```xml
<key>ProgramArguments</key>
<array>
  <string>/bin/zsh</string>
  <string>-lc</string>
  <string>cd /Users/winnie/Documents/trae_projects/qq && PYTHONPATH=. ./.venv/bin/python scripts/run_scheduled_observation.py --env testnet --symbols FETUSDT,OPUSDT --dry-run</string>
</array>
```

Outputs are written under `logs/scheduled_observations/{run_id}/summary.json` and `logs/scheduled_observations/{run_id}/summary.md`.
