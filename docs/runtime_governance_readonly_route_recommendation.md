# T852 — Runtime Governance Read-Only Route Recommendation

## Purpose

Route/model recommendation for future work. Pure, deterministic, no I/O.

## Data

`RuntimeGovernanceRouteRecommendation` (frozen dataclass):
- `work_type: str`
- `recommended_route: str`
- `allowed: bool`
- `risk_level: str` — "low", "medium", "high", "critical"
- `notes: List[str]`

## Recommendations

| work_type | recommended_route | allowed | risk_level | notes |
|---|---|---|---|---|
| pure docs/tests | mimo2.5 | yes | low | No dangerous operations |
| multi-wave dependency queue | mimo2.5pro | yes | medium | Requires API freeze rule |
| live execution | human only | no | critical | Frozen - no autonomous execution |
| secrets management | human only | no | critical | Frozen - no secret access |
| read-only hook implementation | mimo2.5pro with manual review | no | high | Requires manual approval first |

## Functions

- `build_readonly_route_recommendations()` — returns canonical list
- `route_recommendations_to_dict(recommendations)` — list of dicts
- `route_recommendations_to_markdown(recommendations)` — markdown table

## Files

- `core/runtime_governance_readonly_route_recommendation.py`
- `tests/unit/test_runtime_governance_readonly_route_recommendation.py`
