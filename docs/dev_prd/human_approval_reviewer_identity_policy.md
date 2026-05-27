# Human Approval Reviewer Identity Policy

**Task ID:** T1293
**release_hold:** HOLD

## Purpose

Defines who may serve as a human reviewer for approval evidence packs.
Prevents automated, delegated, or anonymous approvals.

## Allowed Reviewers

- Must be a named human operator, not a service account
- Must be listed in the active reviewer registry
- Must have completed reviewer onboarding (acknowledged risk policy)
- Must not be the same person who authored the changes under review

## Prohibited Reviewers

- Service accounts, bots, automated systems
- Any identity that cannot be independently verified
- The author of the frozen file changes (self-approval forbidden)
- Any reviewer whose access has been revoked

## Identity Verification

- Reviewer MUST authenticate via established identity provider
- Identity token MUST be included in evidence pack
- Token MUST be valid at time of approval (expired = reject)
- Identity MUST match reviewer_id field — no delegation

## Reviewer Registry

- Maintained separately from evidence packs
- Entry includes: name, identity provider subject, onboarding date
- Exit includes: name, revocation date, reason
- Registry changes require separate human approval

## Succession

- If primary reviewer unavailable, escalation follows T1299 exception path
- Escalation reviewer must also be in registry
- No auto-promotion to next reviewer — explicit assignment required

## Constraints

- One reviewer per pack — no multi-signature (simplifies audit)
- No batch approval — each pack reviewed individually
- No approval delegation — reviewer must personally read pack
- release_hold = HOLD — reviewer identity does not grant release
