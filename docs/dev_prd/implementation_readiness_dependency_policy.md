# T1196 - Implementation Readiness Dependency Policy

## Rules

### No Circular Dependencies
- Dependency graph must be acyclic
- Cycle detection required before any wave starts
- Circular deps are CRITICAL blockers

### Maximum Depth
- Max dependency chain depth: 5 levels
- Deeper chains require refactoring
- Depth violations are HIGH blockers

### Resolution Order
- Dependencies resolved bottom-up (leaf first)
- Each level fully resolved before next
- Partial resolution not counted

### Frozen Dependency Handling
- Frozen deps cannot be modified
- Frozen deps count as resolved if previously verified
- Changes to frozen deps require authority unfreeze

## Verification

- Dependency graph validated at wave start
- Resolution status checked at readiness scoring
- Unresolved deps block all advancement
