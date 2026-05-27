# Medium Operational No-Network Policy (T1277)

## Purpose

Define network access restrictions for the 13 medium-risk untracked
operational scripts. Scripts must not make live network calls to
exchange endpoints or external services during review.

## release_hold = HOLD

Network restrictions hold regardless of hold state.

## Policy

### P1: No exchange API calls

Scripts must NOT make HTTP/WS calls to:

- Binance API endpoints
- Any cryptocurrency exchange API
- Market data providers (live feeds)

### P2: No outbound network in review

During the review phase, scripts must operate in a fully
offline-capable mode. Permitted data sources:

- Local CSV/JSON files
- Cached data in `artifacts/`
- Mock data generators
- Test fixtures

### P3: No listener sockets

Scripts must NOT open:

- TCP/UDP listener sockets
- WebSocket servers
- HTTP servers

### P4: Network flag requirement

If a script may eventually need network access, it must:

- Default to `network_enabled=False`
- Log all network connection attempts
- Require explicit flag to enable
- Fail gracefully when network unavailable

### P5: DNS resolution prohibition

Scripts must NOT perform DNS resolution for exchange domains
during review. All endpoints must be mocked or disabled.

## Enforcement

- Review checklist T1279 includes network policy checks.
- Static analysis must flag network library usage.
- Any live network call during review is a BLOCKER.
