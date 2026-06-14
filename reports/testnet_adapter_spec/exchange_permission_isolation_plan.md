# Exchange Account and Permission Isolation Plan

**Status: EXCHANGE_PERMISSION_ISOLATION_PLAN_READY**
**Submit: TESTNET_SUBMIT_NOT_ALLOWED**

## Testnet-Only Account

All operations restricted to testnet.binance.vision. No production access.

## Sub-Account Isolation

Dedicated sub-account for automated trading. No shared accounts.

## IP Allowlist Requirement

API keys restricted to known IP addresses. No wildcard IPs.

## Read Permission

Required for balance, position, and order status queries.

## Order Create Permission

Required for order submission. Scoped to allowed symbols only.

## Order Cancel Permission

Required for order cancellation. Must be idempotent.

## Balance Read Permission

Required for account balance queries. Read-only.

## Position Read Permission

Required for position queries. Read-only.

## Withdraw Permission Forbidden

Withdraw permission must not be granted. Any key with withdraw must be revoked.

## Margin/Borrow Forbidden

Margin and borrow permissions forbidden unless explicitly approved by risk review.

## Symbol Allowlist

Only approved symbols allowed. Default: empty (no symbols).

## Notional Cap

Per-order notional cap. Default: 0 (no orders). Requires explicit approval to increase.

## Daily Order Cap

Maximum orders per day. Default: 0. Requires explicit approval to increase.

## Manual Freeze Procedure

Operator can freeze all trading immediately. Freeze requires manual unfreeze.

## Conclusion

EXCHANGE_PERMISSION_ISOLATION_PLAN_READY
TESTNET_SUBMIT_NOT_ALLOWED
