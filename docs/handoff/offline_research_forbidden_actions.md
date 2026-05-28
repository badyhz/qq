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
- ACTIVATE_LIVE
- ENABLE_TESTNET
- auto_promote
- auto-promotion

## Consequences of Violation

Any violation of these rules may result in:
- Loss of research data
- Unintended live trading
- Financial loss
- System instability
