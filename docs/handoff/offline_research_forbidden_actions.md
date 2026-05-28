# Offline Research Forbidden Actions

## Absolutely Forbidden

- Execute any frozen file
- Import any frozen file
- Stage any frozen file
- Modify any pre-existing untracked file
- Delete any pre-existing untracked file
- Rename any pre-existing untracked file
- Use git add .
- Access Binance API
- Submit orders (live or testnet)
- Cancel orders
- Flatten positions
- Enable live trading
- Enable runtime integration
- Enable planner integration
- Use shell=True in subprocess
- Import requests/httpx/aiohttp/urllib/websocket
- Hardcode secrets or API keys

## Forbidden CLI Patterns

- curl, wget (network access)
- binance, exchange (exchange access)
- submit_order, cancel_order, flatten (order operations)
- live_trading, testnet_submit (activation)

## Forbidden Output Patterns

- APPROVED
- SAFE_TO_EXECUTE
- SAFE_TO_IMPORT
- SAFE_TO_DELETE
- SAFE_TO_MOVE
- ACTIVATE_LIVE
- ENABLE_TESTNET
- BACKUP_DONE
- ARCHIVED
- DELETED
- MOVED
- EXECUTED
- IMPORTED
- ACTIVATED
- auto_promote
- auto-promotion

## Forbidden Archive/Delete Actions

- Actually archiving any file
- Actually deleting any file
- Actually moving any file
- Actually renaming any file
- Creating actual backup copies
- Executing rollback commands
- Automated restore operations

## Forbidden Approval Actions (T16001+)

- Granting actual approval from forms
- Auto-approving any form
- Overriding release_hold=HOLD
- Approving immediate backup/archive/delete/move/copy
- Approving live/testnet/runtime activation
- Using completed forms to trigger automated actions
- Using dry-run validation results to authorize actions
- Using outcome matrix to dispatch actions
- Treating "accepted prepare-only" as action authorization

## Consequences of Violation

Any violation of these rules may result in:
- Loss of research data
- Unintended live trading
- Financial loss
- System instability
