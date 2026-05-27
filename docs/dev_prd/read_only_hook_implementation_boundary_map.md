# Read-Only Hook Implementation Boundary Map

## Purpose

Define hard boundaries for what the read-only hook may and may not access. Boundaries are enforced at the import and module level. Crossing a boundary is a hard failure, not a warning.

## Contract

The boundary map divides the system into allowed and forbidden zones. The hook operates exclusively within allowed zones. Any attempt to access a forbidden zone is blocked and logged.

## Fields / Items

| Zone | Status | Description |
|------|--------|-------------|
| Core models | ALLOWED | Pure data models, enums, constants |
| Renderers | ALLOWED | Output formatting, display logic |
| Network | FORBIDDEN | Any network I/O — HTTP, WebSocket, sockets |
| Filesystem | FORBIDDEN | Any file read/write — open(), pathlib, shutil |
| Exchange | FORBIDDEN | Any exchange client — Binance, ccxt, REST/WS |
| Planner | FORBIDDEN | Any planner integration — task queues, schedulers |

## Rules

1. Boundaries are hard walls — not soft suggestions.
2. Import of a forbidden module is a test failure, not a runtime warning.
3. Boundary violations must be caught at test time, not production time.
4. The boundary map is exhaustive — if a zone is not listed as ALLOWED, it is FORBIDDEN.
5. Boundary map changes require human approval and threat model review.

## Safety

- Boundary enforcement is the primary safety mechanism.
- No hook code may import from a forbidden zone.
- Boundary tests run in CI and block merge on failure.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
