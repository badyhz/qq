# Human Review Gate Freeze Dependency Map

## Overview

Frozen files block review gates. If a gate depends on a frozen file, that file must be verified as untampered before the gate may proceed.

## High-Risk Frozen Files (from dirty_workspace_high_risk_freeze_inventory.md)

The following 9 HIGH-risk files create freeze dependencies:

| # | Frozen File | Blocks Gate Type | Reason |
|---|-------------|-----------------|--------|
| 1 | `config.yaml` | RISK_PARAMETER | Risk boundaries, exchange config |
| 2 | `core/risk_manager.py` | TRADING, RISK_PARAMETER | Risk enforcement logic |
| 3 | `core/execution.py` | TRADING, CONNECTION | Order execution logic |
| 4 | `core/order_manager.py` | TRADING | Order lifecycle management |
| 5 | `core/data_feed.py` | CONNECTION | Market data feed |
| 6 | `core/signal_engine.py` | TRADING, PLANNER | Signal generation |
| 7 | `main.py` | TRADING, PLANNER | Entry point, orchestration |
| 8 | `utils/config_loader.py` | CREDENTIAL, RISK_PARAMETER | Config loading, secret resolution |
| 9 | `utils/logger.py` | (all gates) | Logging infrastructure |

## Dependency Rules

1. Any gate that touches a HIGH-risk frozen file requires L3+ approval.
2. Frozen file integrity must be verified before gate proceeds.
3. If frozen file hash mismatch detected, gate status -> BLOCKED.
4. Frozen file verification is a required evidence item on the checklist.

## Gate-to-Freeze Mapping

| Gate Type | Frozen Files Required Verified |
|-----------|-------------------------------|
| TRADING | execution.py, order_manager.py, risk_manager.py, signal_engine.py, main.py |
| CREDENTIAL | config_loader.py, config.yaml |
| CONNECTION | data_feed.py, execution.py |
| PLANNER | signal_engine.py, main.py |
| FROZEN_FILE | (the specific frozen file being modified) |
| RISK_PARAMETER | risk_manager.py, config.yaml, config_loader.py |
