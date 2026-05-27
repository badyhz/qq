# Read-Only Hook Threat Model

## Purpose

Identify and mitigate threats to the read-only hook system. Each threat must have a defined mitigation. The threat model covers the full attack surface of the hook.

## Contract

Threats are enumerated with severity, attack vector, and mitigation. No threat is accepted without a mitigation. The threat model is reviewed before any integration work begins.

## Fields / Items

| # | Threat | Severity | Attack Vector | Mitigation |
|---|--------|----------|---------------|------------|
| 1 | Permission escalation | HIGH | Hook gains write/trade permissions | Hard permission boundary — hook only receives read-only context |
| 2 | Secret leakage | HIGH | Secrets appear in hook output or logs | Output sanitization pass — secrets stripped before emission |
| 3 | Side-effect injection | HIGH | Hook triggers mutations via imports or calls | Import allowlist — only core models permitted |
| 4 | Invariant bypass | MEDIUM | Hook skips or weakens invariant checks | Invariant assertions — checks run before and after every hook |
| 5 | Output tampering | MEDIUM | Hook output modified after generation | Output hashing — hash computed at generation, verified at consumption |

## Rules

1. Each threat must have a mitigation before any code is written.
2. Mitigations must be testable — each has a corresponding test case.
3. New threats discovered during implementation must be added to this model.
4. Threat severity cannot be downgraded without human approval.

## Safety

- Threat model is the source of truth for security requirements.
- No implementation may bypass a mitigation.
- Threat model is reviewed at every phase boundary.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
