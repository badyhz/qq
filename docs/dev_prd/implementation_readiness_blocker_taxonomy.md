# T1193 - Implementation Readiness Blocker Taxonomy

## Blocker Types

### MISSING_TESTS
- **Severity:** HIGH
- **Resolution:** Write required tests, run full suite, verify coverage threshold

### MISSING_DOCS
- **Severity:** MEDIUM
- **Resolution:** Write required documentation, peer review, verify completeness

### SAFETY_VIOLATION
- **Severity:** CRITICAL
- **Resolution:** Fix safety boundary, re-verify all safety constraints, obtain approval

### UNRESOLVED_DEP
- **Severity:** HIGH
- **Resolution:** Resolve dependency, verify no circular deps, update dependency graph

### HIGH_RISK_UNMITIGATED
- **Severity:** CRITICAL
- **Resolution:** Identify risk, implement mitigation, verify mitigation effectiveness

## Severity Levels

| Severity | Behavior |
|---|---|
| CRITICAL | Blocks all advancement, no override without authority |
| HIGH | Blocks advancement, override with approval chain |
| MEDIUM | Blocks advancement, override with single approval |
