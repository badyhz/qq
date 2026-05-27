# T1061-T1160 Safety Boundary Packet

## Frozen Files List

The following files are frozen and must not be modified by T1061-T1160 tasks:

- main.py
- config.yaml
- requirements.txt
- core/data_feed.py
- core/signal_engine.py
- core/risk_manager.py
- core/execution.py
- core/order_manager.py
- core/trade_logger.py
- core/live_runner.py
- core/single_call_recorder.py
- core/evidence_recorder.py
- utils/config_loader.py
- utils/logger.py
- utils/helpers.py
- utils/evidence_recorder.py

## Forbidden Imports

T1061-T1160 modules must NOT import:

- `binance` or any exchange SDK
- `ccxt`
- `live_runner`
- `execution` (core.execution)
- `order_manager` (core.order_manager)
- `data_feed` (core.data_feed) for live data
- Any module that initiates HTTP connections to exchanges
- Any module that reads secrets from environment

## No Live Trading Rules

- No order submission code
- No exchange API calls
- No WebSocket connections to exchanges
- No secret/credential reading
- No live runner invocation
- No production deployment scripts

## Scope Boundary

T1061-T1160 is strictly governance-layer:

- Documentation
- Data models
- Renderers/serializers
- Test suites
- Policy definitions

No runtime integration. No live trading.
