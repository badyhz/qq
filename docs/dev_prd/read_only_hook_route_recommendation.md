# Read-Only Hook Route Recommendation

## Purpose

Define routing rules for which model handles which risk tier in the read-only hook system. Routing ensures high-risk decisions use the strongest model, while low-risk tasks use efficient models. Frozen tasks require human-only handling.

## Contract

Routing is determined by risk tier. Each tier maps to a specific model or actor. No autonomous routing is permitted for live tasks.

## Fields / Items

| Risk Tier | Route | Model | Rationale |
|-----------|-------|-------|-----------|
| HIGH | Autonomous with guard | mimo2.5pro | Strongest reasoning for critical decisions |
| MEDIUM | Autonomous | mimo2.5 | Standard model for moderate complexity |
| LOW | Autonomous | mimo2.5 | Standard model for routine tasks |
| FROZEN | Human-only | N/A | No autonomous execution — human required |

## Rules

1. No autonomous route for live tasks — live tasks always require human approval.
2. HIGH risk tasks use mimo2.5pro for maximum reasoning capacity.
3. LOW and MEDIUM risk tasks use mimo2.5 for efficiency.
4. FROZEN tasks cannot be executed by any agent — human-only.
5. Route decisions must be logged in observability data.

## Safety

- Routing is a safety mechanism — wrong routing is a safety failure.
- Route changes require threat model review.
- FROZEN is the default for any task not explicitly classified.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
