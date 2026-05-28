# Offline Research System Handoff

## Purpose

Create a next-window handoff pack so future conversations can continue without losing context.

## Handoff Pack Contents

- current HEAD and tags
- completed stages
- known test results
- known CLIs
- safety boundaries
- frozen file list
- status of all subsystems
- exact next-window prompt
- no-touch warning
- command cheatsheet
- recovery instructions
- what to do next
- what not to do next

## Safety Boundary

- Offline only. No network. No Binance. No exchange.
- No live trading. No testnet submit. No order placement.
- release_hold must remain HOLD.
- Research output advisory only. Human review required.
- Do not modify, stage, import, execute, delete, or rename pre-existing untracked files.

## CLI

```bash
python3 scripts/build_offline_system_handoff_pack.py \
    --output-dir /tmp/offline_system_handoff_pack \
    --strict \
    --release-hold HOLD
```

## Outputs

- handoff_pack.json
- handoff_pack.md
- handoff_pack_manifest.json
- next_window_prompt.md
