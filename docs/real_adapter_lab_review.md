# Real Adapter Lab Review

**Date:** 2026-05-27
**Scope:** T746-T749 sandbox adapter + governance readiness
**Status:** GO — sandbox adapters validated, governance in place

---

## What shipped

| Module | Purpose |
|---|---|
| `adapters/claude_sandbox_adapter.py` | Sandbox Claude adapter (AsyncAgentAdapter) |
| `adapters/mimo_sandbox_adapter.py` | Sandbox MiMo adapter (AsyncAgentAdapter) |
| `core/real_adapter_policy.py` | Governance: allowlist, budget ceiling, rate limit, kill switch |

### Test counts (pre-compatibility-suite)
- T746: 11/11 PASS
- T747: 24/24 PASS
- T749: 26/26 PASS

---

## Adapter architecture

```
AsyncAgentAdapter (ABC)
├── AsyncMockAdapter          — generic mock (core/)
├── ClaudeSandboxAdapter      — Claude simulation (adapters/)
├── MiMoSandboxAdapter        — MiMo simulation (adapters/)
└── SyncToAsyncAdapter        — sync→async wrapper (core/)
```

All adapters implement the same contract:
- `submit_task()` → request_id
- `poll()` → AsyncTaskResult
- `cancel()` → bool
- `status()` → dict

All are sandbox-only. No API calls. No credentials. No network.

---

## Governance layers

```
Load time:     WorkflowSafetyValidator  → blocks forbidden patterns
Dispatch time: ScheduleSafetyGate       → blocks dangerous categories
Adapter time:  RealAdapterPolicy        → allowlist, budget, rate limit, kill switch
Runtime time:  CircuitBreaker           → trips on repeated failures
```

Four independent safety layers. No coupling between them.

---

## What remains before real adapters

### Must resolve
1. **Real API endpoint configuration** — sandbox adapters simulate; real adapters need actual endpoint URLs
2. **Credential management** — API keys must be in environment variables, never in code
3. **Network timeout tuning** — real API calls have variable latency; need configurable timeouts
4. **Error taxonomy expansion** — real APIs have 429 (rate limit), 500 (server error), 503 (overloaded); current retry policy covers generic failures

### Should resolve
5. **Response validation** — real API responses may be malformed; need schema validation on response
6. **Streaming support** — Claude and MiMo both support streaming; current contract is request/response only
7. **Cost estimation** — real adapters should estimate cost before submitting (token count × price)

### Nice-to-have
8. **Adapter health monitoring** — continuous health checks, not just on-demand status
9. **Fallback adapter** — if Claude is down, auto-fallback to MiMo
10. **Request deduplication** — prevent duplicate submissions

---

## Risk assessment

### Low risk (ready now)
- Sandbox adapters validated against contract
- Governance policy enforces allowlist + budget + rate limit
- Circuit breaker handles repeated failures
- Observability tracks all events

### Medium risk (monitor)
- Real API may have different error patterns than simulated
- Budget ceiling ($10 default) may be too low for real token costs
- Rate limit (10 req/min) may be too conservative or too aggressive

### Acceptable risks
- No streaming (batch mode is fine for initial testing)
- No fallback (single adapter per test is fine for lab)

---

## Go / No-Go

### GO
- Sandbox adapters implement full contract ✅
- Governance policy enforces all safety rules ✅
- Runtime integrates with adapter contract ✅
- Budget + retry + circuit breaker work with adapters ✅
- No frozen files touched ✅
- All tests pass ✅

### NO-GO criteria (none triggered)
- No real API calls in sandbox adapters
- No credentials in code
- No network access from sandbox adapters
- No live trading integration

---

## Recommendation

**Proceed to Real Adapter Lab — Phase 1: API Adapter Skeletons**

Next step: create real API adapter skeletons that:
1. Have the same interface as sandbox adapters
2. Are blocked by default (not on allowlist)
3. Require explicit environment variable configuration
4. Log all requests but don't execute them (dry-run mode)

This validates the integration path without sending real API calls.
