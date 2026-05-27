# Human Review Gate Forbidden Approval Checklist

## Overview

These items must NEVER be approved through the standard gate flow. Each requires explicit human override documented with full justification. Standard APPROVE decisions do not apply.

## Forbidden Categories

### LIVE_TRADING

**Description:** Any action that submits real orders to a live exchange.

**Must NOT approve without explicit human override:**
- Order submission to live Binance API
- Market order execution on live account
- Limit order placement on live account
- Stop-loss activation on live positions
- Any function call that results in real money movement

**Override requirement:** L4 emergency authority with full justification and rollback plan.

### CREDENTIAL_ACCESS

**Description:** Any action that reads, writes, or exposes API keys, secrets, or authentication tokens.

**Must NOT approve without explicit human override:**
- Reading API keys from storage
- Passing credentials to exchange client
- Logging or printing credential values
- Writing credentials to new locations
- Sharing credentials across modules

**Override requirement:** L3+ admin authority with credential audit trail.

### EXCHANGE_CONNECTION

**Description:** Any action that establishes a network connection to an exchange API.

**Must NOT approve without explicit human override:**
- WebSocket connection to live exchange
- REST API call to live exchange
- Connection to production data feed
- Account balance query on live account
- Any network I/O to exchange endpoints

**Override requirement:** L3+ admin authority with connection purpose documented.

### PLANNER_INTEGRATION

**Description:** Any action that connects the planning/strategy layer to execution.

**Must NOT approve without explicit human override:**
- Auto-execution of planner signals
- Planner-driven order submission
- Strategy-to-execution pipeline activation
- Automated rebalancing from planner output
- Any path where planner output becomes order input

**Override requirement:** L3+ admin authority with full pipeline review.

## Enforcement

1. Gate system checks proposed action against forbidden list.
2. If match found, standard approval path is BLOCKED.
3. Only explicit override with documented authority level may proceed.
4. All overrides are logged with: who, when (slot), why, authority level.
5. Override audit trail is itself a frozen artifact.
