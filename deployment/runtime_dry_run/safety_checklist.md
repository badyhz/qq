# Safety Checklist — Server Dry-run Deployment

## Pre-deployment

- [ ] `QQ_MODE=DRY_RUN` in environment
- [ ] `QQ_SUBMIT_PERMISSION=NO_SUBMIT` in environment
- [ ] `QQ_REAL_TRADING_ALLOWED=false` in environment
- [ ] `QQ_TESTNET_SUBMIT_ALLOWED=false` in environment
- [ ] No real API keys in environment
- [ ] No real webhook URLs in environment

## Post-deployment

- [ ] E2E pipeline passes: `PYTHONPATH=. python3 scripts/run_system_dry_run_e2e.py`
- [ ] Dashboard shows "NOT ALLOWED" for real trading
- [ ] Dashboard shows "NOT ALLOWED" for testnet submit
- [ ] No-submit evidence written
- [ ] Alert dedup working
- [ ] No external network calls

## Forbidden

- [ ] Do NOT set `QQ_REAL_TRADING_ALLOWED=true`
- [ ] Do NOT set `QQ_TESTNET_SUBMIT_ALLOWED=true`
- [ ] Do NOT add real API keys
- [ ] Do NOT enable systemd services without review
