# T1192 - Implementation Readiness Score Dimensions

## Dimensions

| Dimension | Weight | Threshold | Description |
|---|---|---|---|
| TEST_COVERAGE | 25% | 80% | Percentage of code paths covered by tests |
| DOCUMENTATION | 15% | 70% | Completeness of required documentation |
| SAFETY_BOUNDARY | 25% | 100% | All safety constraints verified |
| HUMAN_APPROVAL | 15% | 100% | Required human gates approved |
| DEPENDENCY_RESOLUTION | 10% | 100% | All dependencies resolved |
| REGRESSION_RISK | 10% | 90% | No regressions beyond threshold |

## Scoring Formula

```
score = sum(dimension_score * weight for each dimension)
```

## Override Rules

- SAFETY_BOUNDARY below threshold: verdict forced to BLOCKED, no override
- HUMAN_APPROVAL below threshold: verdict forced to HOLD
- Any dimension below threshold: aggregate score capped at threshold percentage
