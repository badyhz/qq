# Frozen Inventory Agent Guardrails

**release_hold = HOLD**
**advisory_only = True**
**no_live = True**
**no_submit = True**
**no_exchange = True**
**no_network = True**
**no_runtime_integration = True**
**no_planner_integration = True**

## Hard Constraints for All Agents

### Never Execute

```text
FORBIDDEN: python3 scripts/live_playbook.py
FORBIDDEN: python3 scripts/run_testnet_order_smoke.py
FORBIDDEN: python3 scripts/submit_approved_candidates.py
FORBIDDEN: python3 scripts/safe_flatten_testnet_symbol.py
FORBIDDEN: python3 scripts/run_controlled_testnet_shift.py
FORBIDDEN: Any execution of frozen files
```

### Never Import

```text
FORBIDDEN: from core.live_runner import LiveRunner
FORBIDDEN: from scripts.submit_replayed_testnet_payload import *
FORBIDDEN: import scripts.run_shadow_observation_experiments
FORBIDDEN: Any import of frozen modules
```

### Never Stage

```text
FORBIDDEN: git add core/live_runner.py
FORBIDDEN: git add scripts/
FORBIDDEN: git add .
FORBIDDEN: git add -A
```

### Always Use Explicit Paths

```text
ALLOWED: git add core/frozen_inventory_audit.py
ALLOWED: git add docs/frozen_inventory/
ALLOWED: git add tests/unit/test_frozen_inventory_audit.py
ALLOWED: git add tests/fixtures/frozen_inventory/
```

## Scanner Safety

The inventory scanner (`core/frozen_inventory_audit.py`):

- Uses only `pathlib`, `hashlib`, `json`, `os` for file analysis
- Never calls `importlib` or `__import__`
- Never calls `subprocess.run` on target files
- Never executes any Python code from target files
- Reads files as raw bytes for hashing
- Reads files as text for keyword detection only
- Skips files above 512KB size limit

## Test Safety

The test suite (`tests/unit/test_frozen_inventory_audit.py`):

- Verifies scanner does not import fixture modules
- Verifies scanner does not execute fixture modules
- Verifies `sys.modules` is not modified by scanning
- Verifies no network libraries in scanner imports

## Enforcement

Any agent violating these guardrails produces a `RESULT = FAIL` outcome.
