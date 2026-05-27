# Medium Operational Import Boundary Policy (T1274)

## Purpose

Define module import boundaries for the 13 medium-risk untracked
operational scripts. Scripts must not import from high-risk modules
without an abstraction layer.

## release_hold = HOLD

Import boundaries are enforced regardless of hold state.

## Policy

### P1: Allowed imports

Medium-risk scripts may import from:

- `utils/` - utility modules
- `core/data_feed.py` - market data (read-only mode)
- `core/signal_engine.py` - signal generation
- `core/risk_manager.py` - risk calculations
- Python standard library
- Approved third-party packages in `requirements.txt`

### P2: Forbidden imports

Medium-risk scripts must NOT import:

- `core/execution.py` - order execution (direct)
- `core/order_manager.py` - order management (direct)
- Any module with `live` in its name
- Any module not listed in `requirements.txt`

### P3: Abstraction layer requirement

To use execution or order management, scripts must import through
a dry-run adapter that enforces simulation mode. The adapter must:

- Intercept all order calls
- Log the intended action
- Return simulated results
- Never reach the exchange API

### P4: No dynamic imports

Scripts must NOT use `importlib.import_module()` or `__import__()`
on runtime-computed strings.

### P5: Circular import prevention

Scripts must not create import cycles with core modules. Import
order: utils -> core (one direction only).

## Enforcement

- Static analysis must verify import statements.
- Review checklist T1279 includes import boundary checks.
