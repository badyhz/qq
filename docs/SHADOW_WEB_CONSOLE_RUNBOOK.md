# Shadow Web Console Runbook

## Start

```bash
python3 scripts/run_shadow_web_console.py
```

## Access

Open browser at:

```
http://127.0.0.1:8765
```

## Options

```bash
--host 127.0.0.1    # Default, local-only
--port 8765         # Default port
--report-dir PATH   # Custom report directory
--smoke-render      # Render HTML and exit (no server)
```

## Dashboard

Displays:
- sample_status
- testnet_gate_status
- clean_positions
- closed_clean_positions
- open_positions
- excluded_positions
- latest lifecycle status
- latest update-only status

## Buttons

| Button | Command |
|--------|---------|
| 扫描新机会 + 更新持仓 | `run_shadow_trading_lifecycle.py --allow-public-http` |
| 只更新已有持仓 | `run_shadow_position_update_only.py --allow-public-http` |
| 刷新样本门禁 | `run_sample_collection_gate.py` |
| 打印当前状态 | `print_shadow_operator_status.py` |

## Reports

Click links to view:
- Latest Lifecycle Result
- Latest Update-Only Result
- Latest Sample Gate
- Latest Scorecard

## Action Log

Each button click is logged to:

```
reports/strategies/YYYY-MM-DD_shadow_web_console_actions.jsonl
```

## Safety Boundary

- Local only (127.0.0.1)
- No public host binding
- No order
- No account
- No testnet/live
- No secret
- No .env
- No daemon
- No scheduler
- No websocket
- Buttons only trigger fixed allowlist commands
- Report viewer only reads reports/strategies directory
- No path traversal allowed

## Troubleshooting

Port already in use:
```bash
python3 scripts/run_shadow_web_console.py --port 8766
```

Reports not found:
```bash
python3 scripts/run_shadow_trading_lifecycle.py --allow-public-http
```

Host rejected:
Only 127.0.0.1 and localhost are allowed. Do not use 0.0.0.0 or external IPs.
