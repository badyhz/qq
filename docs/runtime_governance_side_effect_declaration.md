# Runtime Governance Side-Effect Declaration (T830)

## Purpose

Formal declaration of side-effects for runtime governance components T826-T829. Each component declares what it reads/writes and whether it triggers dangerous actions. Deterministic, frozen dataclass.

## Components

| Component | Reads Mem | Writes Mem | Reads Files | Writes Files | Network | Orders | Mutate | Secrets | Verdict |
|-----------|-----------|------------|-------------|--------------|---------|--------|--------|---------|---------|
| T826: runtime_governance_contract | Y | N | Y | N | N | N | N | N | PASS |
| T827: runtime_governance_artifact_index | Y | N | Y | N | N | N | N | N | PASS |
| T828: runtime_governance_blocker_summary | Y | N | Y | N | N | N | N | N | PASS |
| T829: runtime_governance_frozen_boundary_map | Y | N | Y | N | N | N | N | N | PASS |

## Verdict Rules

- `places_orders=True` -> BLOCKED
- `mutates_account=True` -> BLOCKED
- `accesses_secrets=True` -> BLOCKED
- Otherwise -> PASS

## Files

- `core/runtime_governance_side_effect_declaration.py` - Implementation
- `tests/unit/test_runtime_governance_side_effect_declaration.py` - Tests
