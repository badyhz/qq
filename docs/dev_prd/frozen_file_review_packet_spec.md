# Frozen File Review Packet Specification (T1469)

## Purpose

Defines the structured output format for frozen file inspections.

## Packet Structure

```
FrozenFileReviewPacket:
  file_path: str              # absolute path to frozen file
  risk_level: str             # HIGH | MEDIUM | LOW
  frozen_reason: str          # why file was frozen
  inspection_timestamp: str   # ISO 8601 UTC
  inspector_id: str           # reviewer identifier
  findings: list[Finding]     # inspection findings
  evidence_refs: list[str]    # references to evidence artifacts
  recommendation: str         # UNLOCK | HOLD | ESCALATE
  confidence: float           # 0.0 - 1.0
```

## Finding Structure

```
Finding:
  category: str        # IMPORT_BOUNDARY | SIDE_EFFECT | CREDENTIAL_ACCESS | NETWORK_CALL | OTHER
  severity: str        # CRITICAL | HIGH | MEDIUM | LOW | INFO
  description: str     # plain text finding
  location: str        # file:line or module reference
  remediation: str     # suggested fix or action
```

## Validation Rules

- `file_path` must exist in frozen file inventory
- `risk_level` must match frozen inventory classification
- `inspection_timestamp` must be ISO 8601 UTC
- `confidence` must be in [0.0, 1.0]
- At least one finding required
- `recommendation` must be one of: UNLOCK, HOLD, ESCALATE

## Constraints

- Pure dataclass model. No side effects.
- No runtime execution. Documentation only.
- Release hold: HOLD
