# Read-Only Hook Forbidden Transition List

## Purpose

Defines phase transitions that are explicitly forbidden.

## Content

- design -> live_execution: FORBIDDEN
- read_only -> write_access: FORBIDDEN
- dry_run -> live_trading: FORBIDDEN
- governance_design -> runtime_integration: FORBIDDEN

## Safety Statement

No live trading. No submit. No exchange. No secrets. No planner. Read-only design artifacts only.
