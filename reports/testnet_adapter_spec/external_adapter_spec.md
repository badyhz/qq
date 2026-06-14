# External Testnet Adapter Design Specification

**Phase: DESIGN_ONLY — No implementation in this phase**
**Submit: TESTNET_SUBMIT_NOT_ALLOWED**
**Adapter Mode: ARCHITECTURE_ONLY**

## Adapter Purpose

Provide a safe, auditable interface to Binance testnet for order lifecycle management. Design-only phase — no implementation.

## Non-Goals

No real submit, no real credentials, no live trading, no auto-submit, no real network calls in this phase.

## Supported Future Exchange Profile

Binance testnet (testnet.binance.vision) only; no production endpoints. Spot and USDⓈ-M futures. REST API v3/v1. HMAC-SHA256 signing.

## Future Method Boundaries

load_connection_profile, validate_permissions, build_signed_request, submit_order, cancel_order, fetch_balance, fetch_positions, fetch_order_status, reconcile.

## Forbidden Current Methods

No real network calls, no real API keys, no real signatures, no real order submission, no ccxt client instantiation. Submit remains locked and testnet submit is not allowed until governance unlock.

## Credential Dependency

Requires encrypted credential vault with access control, audit logging, key rotation, and redaction. Not implemented in this phase.

## Request Signing Dependency

Requires HMAC-SHA256 canonical request construction with timestamp, nonce, and payload hash. Not implemented in this phase.

## Network Transport Dependency

Requires HTTPS-only transport with TLS 1.2+, certificate pinning, timeout, retry, and rate limiting. Not implemented in this phase.

## Rate Limit Dependency

Requires per-endpoint rate limits with exponential backoff and cool-down. Not implemented in this phase.

## Cancel Dependency

Requires idempotent cancel, terminal order handling, unknown order handling, and cancel audit trail. Not implemented in this phase.

## Reconciliation Dependency

Requires real balance/position fetch, staleness detection, mismatch handling, and manual override. Not implemented in this phase.

## Audit Dependency

Requires tamper-evident hash chain, external storage, 90-day retention, and export capability. Not implemented in this phase.

## Human Approval Dependency

Requires multi-party approval with expiration, risk summary, cancel plan, and rollback plan. Not implemented in this phase.

## Kill Switch Dependency

Requires kill switch armed by default, blocking all submits, with manual 2-person unlock. Not implemented in this phase.

## Rollback Dependency

Requires point-in-time restore, artifact preservation, and audit log continuity. Not implemented in this phase.

## Conclusion

EXTERNAL_TESTNET_ADAPTER_SPEC_VALID
TESTNET_SUBMIT_NOT_ALLOWED
