# Promotion Readiness Scoring Specification (T1470)

## Purpose

Defines how promotion readiness is quantified for frozen files.

## Scoring Dimensions

| Dimension | Weight | Range | Description |
|---|---|---|---|
| import_boundary | 0.20 | 0-100 | No forbidden imports |
| side_effect_free | 0.20 | 0-100 | No uncontrolled side effects |
| credential_safe | 0.15 | 0-100 | No hardcoded secrets |
| network_safe | 0.15 | 0-100 | No unauthorized network calls |
| test_coverage | 0.15 | 0-100 | Adequate test coverage |
| documentation | 0.10 | 0-100 | Documentation complete |
| human_review | 0.05 | 0-100 | Human reviewer approval |

## Score Model

```
PromotionReadinessScore:
  file_path: str
  computed_at: str                    # ISO 8601 UTC
  dimensions: dict[str, float]        # dimension -> score (0-100)
  weighted_total: float               # weighted sum (0-100)
  threshold: float                    # minimum to promote (default: 80.0)
  meets_threshold: bool               # weighted_total >= threshold
  blockers: list[str]                 # dimensions below minimum (50.0)
  recommendation: str                 # PROMOTE | HOLD | ESCALATE
```

## Decision Logic

```
if any dimension < 50.0:
  recommendation = HOLD
  blockers = [dimensions below 50.0]
elif weighted_total >= threshold:
  recommendation = PROMOTE
else:
  recommendation = HOLD
```

## Constraints

- Pure computation. No side effects.
- Threshold is configurable per file but defaults to 80.0.
- Blocker threshold is fixed at 50.0.
- Release hold: HOLD
