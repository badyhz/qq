# No-Submit Release Gate Runtime Policy

Task: T1187

## Rules

### No LiveRunner

LiveRunner must not be instantiated or started.

### No ExecutionEngine.run_once with Live Connector

ExecutionEngine.run_once must not be called with a live connector.

### No Preflight Bypass

Preflight checks must not be skipped or overridden.
