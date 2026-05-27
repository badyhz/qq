# T1198 - Implementation Readiness Rollback Policy

## Rules

### Every Change Must Be Reversible
- No irreversible changes without explicit approval
- Reversibility verified before deployment
- Irreversible changes are CRITICAL blockers

### Rollback Plan Documented
- Rollback steps listed for every change
- Steps must be executable and ordered
- Plan reviewed before gate approval

### Verification After Rollback
- Rollback must restore prior state
- Verification tests run post-rollback
- Rollback failure is CRITICAL blocker

## Structure

Each rollback entry:
- change_id: unique identifier
- rollback_steps: ordered tuple of steps
- verification_command: command to verify rollback
- reversible: boolean flag
