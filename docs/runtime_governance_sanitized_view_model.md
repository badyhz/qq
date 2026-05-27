# Runtime Governance Sanitized View Model

**Module:** `core/runtime_governance_sanitized_view_model.py`
**Tests:** `tests/unit/test_runtime_governance_sanitized_view_model.py`
**Purpose:** Expose governance data with field-level redaction. No secrets leak through sanitized views.

## Dataclasses

- `RuntimeGovernanceSanitizedField` — field descriptor (name, type, sensitivity, allowed, redaction rule)
- `RuntimeGovernanceSanitizedView` — immutable view with fields, verdict, notes

## Sensitivity Levels

| Level | Description | Allowed in view |
|-------|-------------|-----------------|
| public | Non-sensitive operational data | yes |
| internal | Internal metrics, safe for team | yes |
| sensitive | Needs care but not secret | yes |
| secret | API keys, balances, raw orders, credentials | **always NO** |

## Views

| View ID | Purpose |
|---------|---------|
| preflight_summary | Preflight check results |
| regression_summary | Test regression results |
| safety_summary | Safety/risk check results |
| artifact_summary | Artifact verification results |

## Functions

- `build_runtime_governance_sanitized_view(view_id)` — build view; raises ValueError on unknown id or policy violation
- `sanitized_view_to_dict(view)` — serialize to dict
- `sanitized_view_to_markdown(view)` — deterministic markdown
- `summarize_sanitized_view(view)` — field count summary by sensitivity

## Safety Invariant

Secret fields (`sensitivity="secret"`) must always have `allowed=False`. The builder enforces this at construction time.
