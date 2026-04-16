# QQ Trading Bot

This project is a deployable dry-run / websocket trading system that can run on Tencent Cloud.

## What it does
- Runs in `dry-run` mode by default.
- Supports `mock` data for quick validation.
- Supports Binance futures public websocket for real market validation.
- Generates `trades.csv` for replay and dashboard analysis.
- Keeps a clean `core/` project layout and leaves `live` execution hooks ready.

## Project layout
- `main.py`: main loop and orchestration
- `config.yaml`: runtime configuration
- `requirements.txt`: deployment dependencies
- `dashboard.py`: post-trade analytics
- `core/data_feed.py`: mock and websocket candle feed
- `core/signal_engine.py`: state machine and score engine
- `core/risk_manager.py`: sizing, cooldown, and circuit breaker
- `core/order_manager.py`: open position tracking and dry-run exits
- `core/execution.py`: dry-run and live execution bridge
- `core/exchange.py`: Binance futures wrapper for live mode
- `core/trade_logger.py`: CSV trade recorder
- `utils/indicators.py`: technical indicator helpers
- `utils/logger.py`: logging setup

## Tencent Cloud deployment
1. Create an Ubuntu server that can access Binance.
2. Upload the whole project directory.
3. Install Python 3.10+.
4. Create a virtual environment.
5. Install dependencies.
6. Keep `mode: "dry-run"` on the first run.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Running in background
Use `screen`, `tmux`, or `systemd`.

```bash
screen -S qq-bot
source .venv/bin/activate
python3 main.py
```

Detach with `Ctrl+A` then `D`.

## Quick start script

```bash
chmod +x start.sh
./start.sh
```

## Systemd service

If your project is uploaded to `/root/qq`, you can install the included service file:

```bash
cp deploy/qq-bot.service /etc/systemd/system/qq-bot.service
systemctl daemon-reload
systemctl enable qq-bot
systemctl start qq-bot
systemctl status qq-bot
```

## Dashboard
After trades are generated:

```bash
python3 dashboard.py
```

## Configuration workflow
- Quick smoke test: `mode=dry-run`, `data_mode=mock`
- Market validation: `mode=dry-run`, `data_mode=websocket`
- Live mode: only after you fill Binance API keys and validate the system

## Safety note
`live` mode places real futures orders. Keep it disabled until you finish dry-run validation.
