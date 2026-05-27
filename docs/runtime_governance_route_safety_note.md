# Runtime Governance Route Safety Note

## Overview

T822 defines routing rules that map task risk tiers to AI model selection and
execution autonomy levels.

## Content Summary

| Risk Tier | Routing | Autonomy |
|-----------|---------|----------|
| Low: pure docs/tests | mimo2.5 | Autonomous ok |
| Medium: multi-agent dependency DAG | mimo2.5pro | Autonomous with review gate |
| High: live submit / secrets / exchange | Human-controlled only | No autonomous live submit |

## Key Constraint

Autonomous live submit is never recommended. All exchange-facing actions
require explicit human approval.

## Files

- Builder: `core/runtime_governance_route_safety_note.py`
- Tests: `tests/unit/test_runtime_governance_route_safety_note.py`
