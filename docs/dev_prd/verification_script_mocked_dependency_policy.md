# Verification Script Mocked Dependency Policy

**Task ID:** T1284
**release_hold:** HOLD
**Status:** Active

## Policy

All external dependencies in verification scripts must be mocked or stubbed.

## What Counts as External

- Exchange APIs (Binance REST, WebSocket)
- HTTP clients (requests, httpx, aiohttp)
- File system writes outside /tmp or test directories
- Database connections
- Cloud services (S3, logging backends)

## Mock Requirements

1. Mocks must be declared at the TOP of the test function or fixture
2. Mocks must return realistic but deterministic data
3. Mocks must NOT call through to real implementations
4. Patch targets must use `module.path.to.function` not just `function_name`

## Review Checklist

- [ ] All external calls identified
- [ ] Each external call has a corresponding mock
- [ ] No mock is a pass-through (i.e., no `side_effect=some_real_func`)
- [ ] Mock return values are plausible for the test scenario
- [ ] No mocking of internal-only modules (over-mocking is a smell)

## Rejection Criteria

- Unmocked exchange call = REJECT
- Mock that calls real network = REJECT
- Missing mock for file write outside test dir = REJECT
