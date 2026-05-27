# Human Review Gate Overview

## Purpose

Human review gate system enforces mandatory human approval before any action that could affect live trading state, credentials, exchange connections, or risk boundaries. No automated agent may bypass a gate without explicit human override.

## Scope

Applies to all code paths that touch:
- Order submission or execution
- Credential or secret access
- Exchange API connections
- Planner or strategy integration
- Frozen file modifications
- Risk parameter changes

Out of scope: read-only queries, dry-run simulations, log analysis.

## Gate Types

| Gate Type | Description |
|-----------|-------------|
| TRADING | Blocks live order submission |
| CREDENTIAL | Blocks secret/credential access |
| CONNECTION | Blocks exchange API connection |
| PLANNER | Blocks planner integration |
| FROZEN_FILE | Blocks modification of frozen files |
| RISK_PARAMETER | Blocks risk boundary changes |

## Enforcement Model

1. Agent proposes action.
2. Gate checks required evidence checklist.
3. Gate checks forbidden approval list.
4. If all checks pass, status transitions to PENDING_APPROVAL.
5. Human reviews and issues decision (APPROVE / REJECT / ESCALATE / DEFER / CONDITIONAL_APPROVE).
6. Action proceeds only on APPROVE or CONDITIONAL_APPROVE (with conditions met).

No gate may be auto-approved. Every gate requires a human decision record.

## Safety Statement

This system does NOT perform live trading. All trading defaults to dry-run mode. No order submission, exchange connection, or credential access occurs without explicit human approval through the gate system. The gate system is a safety layer, not a trading layer.
