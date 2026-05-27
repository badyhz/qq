# Runtime Governance PRD

## Project Title

Runtime Governance / Read-only Safety Control Plane

## Background

The repo is building a quant trading system for Binance. Current work is safety/governance/control-plane before any runtime or live integration.

## Completed Layers

- governance failure taxonomy/reporting (T786-T789)
- governance support stack (T790-T793)
- runtime governance contract/preflight (T794-T797)
- runtime governance expansion and closeout (T798-T825)
- read-only integration design (T826-T857)

## Product/Engineering Goal

Create deterministic, testable, auditable safety layers before any runtime integration. Ensure every future integration step has:

- contract
- policy boundary
- evidence packet
- regression packet
- manual review gate
- release hold

## Non-Goals

- no live trading
- no real order placement
- no exchange connection
- no account mutation
- no secrets access
- no autonomous planner execution

## Design Principles

- pure functions first
- deterministic outputs
- no timestamps/random/env reads unless explicitly scoped
- dataclass + serializer + markdown + tests
- commit per task
- human controls phase advance

## Agent Execution Model

- PRD-driven
- task_queue-driven
- acceptance-driven
- human-reviewed
