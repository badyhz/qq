# Request Signing Architecture

**signing_mode=ARCHITECTURE_ONLY**
**real_secret_used=false**
**request_sendable=false**
**network_called=false**
**submit_allowed=false**

## Canonical Request Format

METHOD\nPATH\nTIMESTAMP\nNONCE\nPAYLOAD_HASH. Architecture-only.

## Timestamp Policy

Unix epoch milliseconds. Must be within 5 seconds of server time. Clock skew handling required.

## Nonce Policy

UUID v4 per request. Never reused within timestamp window.

## Payload Hashing

SHA-256 of request body. Empty string for GET requests.

## Signature Algorithm Placeholder

HMAC-SHA256 of canonical string with API secret. Placeholder only — no real signing.

## Redaction Requirement

Secret never logged. Signature redacted in audit logs. Only last 4 chars of key visible.

## Replay Protection

Timestamp + nonce combination prevents replay. Server-side nonce cache recommended.

## Clock Skew Handling

Requests outside 5-second window rejected. NTP sync recommended.

## Signing Failure Handling

Signing failure aborts request. No fallback to unsigned. Incident logged.

## Audit Event Requirement

Every signing attempt logged: timestamp, key_id (redacted), success/failure, reason.

## Credential Dependency

Signing requires credential vault with API secret. Not implemented.

## No-Submit Dependency

Signing does not grant submit permission. Submit gate remains locked.

## Conclusion

REQUEST_SIGNING_ARCHITECTURE_READY
TESTNET_SUBMIT_NOT_ALLOWED
