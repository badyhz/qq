# Credential Vault Architecture

**credential_vault_mode=ARCHITECTURE_ONLY**
**real_credentials_enabled=false**
**env_secret_read=false**
**submit_allowed=false**

## Secret Storage Backend

AES-256-GCM encrypted file-based storage with master key derived from operator passphrase. Architecture-only.

## Encryption at Rest

All credential values encrypted at rest with AES-256-GCM. Master key never stored in plaintext.

## Encryption in Transit

TLS 1.2+ required for all credential access. Certificate pinning recommended.

## Access Control

Role-based access: operator (read), reviewer (read), admin (read/write). No anonymous access.

## Operator Identity

Operator must authenticate with MFA before accessing credentials. Identity logged.

## Reviewer Identity

Reviewer must authenticate independently. Cannot be same person as operator.

## Least Privilege

Each credential set scoped to minimum required permissions. No blanket access.

## Read-Only Key Class

Separate key class for balance/position reads. Cannot submit orders.

## Trade Key Class

Trade-scoped key class. Can submit/cancel orders. Cannot withdraw.

## Withdraw Permission Forbidden

Withdraw permission must be explicitly forbidden on all keys. Any key with withdraw permission must be revoked immediately.

## Rotation Policy

Keys rotated every 90 days. Rotation requires human approval. Old keys revoked after rotation.

## Revocation Policy

Emergency revocation available 24/7. Revocation logged and requires post-incident review.

## Redaction Policy

All credential values redacted in logs, reports, and outputs. Only last 4 chars visible.

## Audit Trail

Every credential access logged with timestamp, operator, action, and result. Tamper-evident.

## Incident Response

Credential compromise triggers immediate revocation, audit review, and stakeholder notification.

## Environment Isolation

Testnet and production credentials stored in separate vaults. No cross-environment access.

## Manual Approval Dependency

Credential creation, rotation, and revocation require human approval. No automated credential lifecycle.

## Conclusion

CREDENTIAL_VAULT_ARCHITECTURE_READY
TESTNET_SUBMIT_NOT_ALLOWED
