# Paper Trading Deployment

Server deployment pack for paper trading ops. **This is a deployment pack, not a real trading system.**

## What This Does

- Validates server readiness (preflight)
- Runs canary dry-run to verify all runners work
- Generates systemd/timer install plans (does not install)
- Generates cron install plans (does not install)
- Generates logrotate examples
- Checks runtime directory layout
- Produces server health reports
- Generates rollback plans
- Safety regression scans all deployment files

## What This Does NOT Do

- Does NOT execute real trades
- Does NOT send real Feishu alerts
- Does NOT auto-enable systemd services
- Does NOT auto-write crontab
- Does NOT read real exchange credentials
- Does NOT install anything automatically

## Quick Start

```bash
# Run full deployment suite
PYTHONPATH=. python3 scripts/run_paper_ops_deployment_suite.py

# Individual checks
PYTHONPATH=. python3 scripts/run_paper_ops_server_config_check.py
PYTHONPATH=. python3 scripts/run_paper_ops_deployment_preflight.py
PYTHONPATH=. python3 scripts/run_paper_ops_canary_dry_run.py
PYTHONPATH=. python3 scripts/run_paper_ops_server_health_report.py
PYTHONPATH=. python3 scripts/run_paper_ops_install_plan.py
PYTHONPATH=. python3 scripts/run_paper_ops_rollback_plan.py
```

## Server Config

Edit `config/deployments/paper_trading_ops_server.example.yaml`:
- Set `qq_repo_path_candidates` to your server paths
- Set `scanner_path_candidates` to your scanner paths
- All safety flags must be `false`

## Preflight

Checks that:
- Repo path exists
- Scanner path exists (warning if missing)
- Required scripts exist
- Required packages exist
- Deploy examples exist
- Runtime directories can be created

## Canary Dry-Run

Runs key modules in sequence to verify they work:
1. Server config check
2. Deployment preflight
3. Log source check
4. State audit
5. Strategy metrics
6. Signal dashboard
7. Daily bundle
8. Alert payload
9. Deployment safety regression

## Install Plan

Generates install commands as text. **Manual confirmation required.**

To actually install (after reviewing the plan):
1. Copy systemd files: `sudo cp deploy/systemd/*.example /etc/systemd/system/`
2. Copy logrotate: `sudo cp deploy/logrotate.d/*.example /etc/logrotate.d/`
3. Reload: `sudo systemctl daemon-reload`
4. Enable: `sudo systemctl enable <timer-name>`
5. Start: `sudo systemctl start <timer-name>`

## Rollback

Generates rollback commands as text. **Manual confirmation required.**

To rollback:
1. Stop timers: `sudo systemctl stop <timer-name>`
2. Disable: `sudo systemctl disable <timer-name>`
3. Remove files: `sudo rm /etc/systemd/system/<file>`
4. Reload: `sudo systemctl daemon-reload`

## Why No Auto-Install?

This system monitors paper trading — no real money is at risk from a missed scan. Auto-installing systemd services or crontab entries could:
- Conflict with existing services
- Cause unexpected resource usage
- Create security risks if paths are wrong

Always review and install manually.

## Why No Real Trading?

This is a paper trading monitoring system. It:
- Reads scanner logs (read-only)
- Generates paper positions (no real orders)
- Produces reports (no real alerts)
- Grades strategy quality (no real P&L)

Real trading requires explicit authorization and a separate, hardened execution path.
