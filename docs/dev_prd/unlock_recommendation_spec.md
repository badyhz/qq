# Unlock Recommendation Specification (T1472)

## Purpose

Defines the recommendation format for unlocking frozen files.

## Recommendation Structure

```
UnlockRecommendation:
  file_path: str                       # target frozen file
  recommendation_timestamp: str        # ISO 8601 UTC
  readiness_score: PromotionReadinessScore
  approval_transcript: HumanApprovalTranscript
  unlock_conditions_met: bool          # all conditions satisfied
  remaining_conditions: list[str]      # conditions not yet met
  risk_level_after_unlock: str         # post-unlock risk classification
  governance_policy: str               # post-unlock governance policy
  rollback_plan: str                   # rollback procedure reference
  recommendation: str                  # UNLOCK | HOLD
```

## Prerequisites for UNLOCK

1. Promotion readiness score meets threshold (>= 80.0, no blockers)
2. Human approval transcript with decision = APPROVE
3. Risk acknowledgement = True
4. Rollback acknowledgement = True
5. All conditions from approval transcript met

## Post-Unlock Governance

- File transitions from FROZEN to GOVERNED
- Subject to medium-risk or low-risk policy based on post-unlock classification
- Must maintain test coverage
- Import boundaries still enforced
- No-submit gate still applies if applicable

## Constraints

- Recommendation is advisory. Actual unlock requires human authorization.
- No automated unlock. Documentation only.
- Release hold: HOLD
