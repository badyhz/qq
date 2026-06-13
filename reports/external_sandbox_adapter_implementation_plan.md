# External Sandbox Adapter Implementation Plan

**Phase: DESIGN_ONLY — No implementation in this phase**
**Submit: NOT_ALLOWED**

## Adapter Boundaries

Define clear boundary between simulation and real exchange. All methods must be simulation-only in this phase.

## Allowed Future Methods

load_connection_profile, validate_permissions, build_signed_request, submit_order, cancel_order, fetch_balance, fetch_positions, fetch_order_status

## Forbidden Current Methods

No real network calls, no real API keys, no real signatures, no real order submission

## Network Transport Requirements

HTTPS only, TLS 1.2+, certificate pinning, request timeout, retry with backoff

## Request Signing Requirements

HMAC-SHA256, timestamp validation, recvWindow parameter, canonical string construction

## Credential Vault Requirements

Encrypted at rest, access control, audit logging, key rotation, no environment variables

## Rate Limit Requirements

Per-endpoint limits, order rate limits, cancel rate limits, exponential backoff, cool-down

## Cancel Safety Requirements

Idempotent cancel, terminal order handling, unknown order handling, audit trail

## Reconciliation Requirements

Real balance fetch, real position fetch, staleness detection, mismatch handling, manual override

## Audit Logging Requirements

Tamper-evident chain, external storage, retention policy, export capability

## Human Approval Requirements

Multi-party approval, expiration, risk summary, cancel plan, rollback plan

## Rollback Requirements

Point-in-time restore, artifact preservation, audit log continuity

## Conclusion

EXTERNAL_SANDBOX_ADAPTER_PLAN_VALID
NO_SUBMIT_ALLOWED
