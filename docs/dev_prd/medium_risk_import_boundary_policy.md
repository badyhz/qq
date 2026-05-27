# Medium-Risk Import Boundary Policy (T1175)

## Purpose

Prevent medium-risk scripts from directly coupling to high-risk modules.

## Rules

### R1: Must not import from HIGH-risk modules directly

Medium-risk scripts must not import from modules classified as HIGH risk.
High-risk modules include:

- `core/execution.py` (live order submission)
- `core/order_manager.py` (live order tracking)
- Any module under a freeze boundary

### R2: Must use abstraction layer

When a medium-risk script needs functionality that lives in a high-risk
module, it must access it through an abstraction layer. Examples:

- `core/adapter_safety.py` wraps exchange calls with safety checks
- `core/adapter_preflight.py` validates before execution
- Dedicated interface modules that expose only safe operations

### R3: Must document all imports

Every medium-risk script must include a comment block at the top
listing all imports and their risk classification:

```python
# IMPORTS
# - core.signal_engine       : MEDIUM (allowed)
# - core.adapter_safety      : MEDIUM (abstraction layer)
# - core.execution            : HIGH (not imported - uses abstraction)
```

## Verification

The promotion checklist (T1179) includes an import audit step.
The import boundary model (T1213) can be used programmatically.
