# T1199 - Implementation Readiness Next Wave Policy

## Rules

### Wave N+1 Cannot Start Until Wave N Passes Readiness Scoring
- Readiness score must be PASS
- All blockers resolved
- All hold states CLEAR

### Human Approval Between Waves
- REVIEW_GATE required between waves
- Evidence from wave N scoring provided
- Approval chain cannot be shortened

### Wave Transition Checklist
- Wave N readiness score: PASS
- All tests passing
- All blockers resolved
- Regression check clean
- Human approval recorded
- Rollback plan verified

## Recommendation

Next wave tasks recommended based on:
- Dependency resolution status
- Priority ordering
- Risk assessment
- Resource availability
