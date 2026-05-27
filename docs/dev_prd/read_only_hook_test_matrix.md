# Read-Only Hook Test Matrix

## Purpose

Define the test categories and coverage requirements for the read-only hook system. All tests must be runnable without live connectivity, exchange access, or planner integration.

## Contract

Tests are organized into four categories. Each category has defined scope and acceptance criteria. No test may require live trading or exchange connectivity.

## Fields / Items

| Category | Scope | Acceptance Criteria |
|----------|-------|---------------------|
| Unit tests | Individual hook functions | All public functions covered, pass rate 100% |
| Integration tests (read-only) | Hook lifecycle end-to-end | Full invocation cycle verified, no side effects |
| Boundary tests | Import and access boundaries | All forbidden imports blocked, all allowed imports pass |
| Forbidden-import tests | Static analysis of imports | No forbidden module in import graph |

## Rules

1. No live tests — all tests run against mocks or local fixtures.
2. No exchange tests — no Binance, ccxt, or REST/WS calls in any test.
3. No planner tests — no task queue or scheduler interaction.
4. Test coverage must be 100% for boundary enforcement paths.
5. All tests must pass before any phase transition.

## Safety

- Tests are the enforcement mechanism for boundaries.
- Failing tests block merge and deployment.
- Test fixtures must not contain real credentials or API keys.

## Status

- Status: DESIGN_ONLY
- No live trading authorization
- No runtime integration
- No planner integration
