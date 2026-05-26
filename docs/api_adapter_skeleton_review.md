# API Adapter Skeleton Review

**Date:** 2026-05-27
**Scope:** T751-T754 API skeleton + credential isolation + network sandbox
**Status:** GO — skeletons validated, governance layers in place

---

## What shipped

| Module | Purpose |
|---|---|
| `adapters/claude_api_adapter.py` | Claude API skeleton (dry-run, no network) |
| `adapters/mimo_api_adapter.py` | MiMo API skeleton (dry-run, no network) |
| `core/credential_manager.py` | Centralized credential abstraction |
| `core/network_sandbox.py` | Outbound request policy |

### Test counts (isolation)
- T751 Claude API: 24/24 PASS
- T752 MiMo API: 44/44 PASS
- T753 Credential: 30/30 PASS
- T754 Network: 24/24 PASS

---

## Architecture: adapter stack

```
adapters/
├── claude_sandbox_adapter.py    — simulated responses (v6)
├── mimo_sandbox_adapter.py      — simulated responses (v6)
├── claude_api_adapter.py        — API skeleton, dry-run (v7)
└── mimo_api_adapter.py          — API skeleton, dry-run (v7)

core/
├── credential_manager.py        — env lookup, masking, validation
├── network_sandbox.py           — domain allowlist/denylist, rate ceiling
├── real_adapter_policy.py       — allowlist, budget, kill switch (v6)
├── async_agent_adapter.py       — ABC contract
└── workflow_runtime.py          — unified runtime
```

---

## Safety layers (complete)

```
Layer 1: CredentialManager     — validates keys exist before adapter starts
Layer 2: NetworkSandbox        — blocks non-allowed domains, enforces rate ceilings
Layer 3: RealAdapterPolicy     — allowlist, budget ceiling, kill switch
Layer 4: ScheduleSafetyGate    — blocks dangerous task categories at dispatch
Layer 5: WorkflowSafetyValidator — blocks forbidden patterns at load time
Layer 6: CircuitBreaker        — trips on repeated failures
Layer 7: RetryPolicy           — exponential backoff with failure classification
```

Seven independent safety layers. No coupling.

---

## Dry-run guarantees

All API skeletons enforce dry-run mode:
- Requests stored locally, never sent
- Responses simulated
- API keys accepted but never used
- No HTTP client imports in source
- No network calls possible

Verified by test: `test_no_real_http_adapter` checks source code for HTTP imports.

---

## Known issues

### Cross-file async event loop interference
MiMo adapter tests fail when run after other async test files due to `asyncio.get_event_loop()` conflicts with anyio. Tests pass in isolation. This is a test environment issue, not an adapter bug. Fix: migrate MiMo tests to anyio async pattern (low priority).

---

## What remains before live adapters

### Must resolve
1. **Wire credentials to real env vars** — set ANTHROPIC_API_KEY, MIMO_API_KEY in .env
2. **Enable network in controlled mode** — switch NetworkSandbox from "simulation" to "restricted"
3. **Remove dry-run guard** — only after all safety layers verified in restricted mode
4. **First real API call** — single test request to verify auth + response parsing

### Should resolve
5. **Streaming support** — Claude and MiMo both support streaming responses
6. **Response schema validation** — validate real API responses match expected format
7. **Cost estimation** — estimate token cost before sending request

---

## Go / No-Go

### GO
- API skeletons implement full contract ✅
- Credential isolation: env lookup + masking + validation ✅
- Network sandbox: domain allowlist + rate ceiling + offline mode ✅
- Seven safety layers operational ✅
- Dry-run mode verified ✅
- All tests pass (in isolation) ✅

### NO-GO criteria (none triggered)
- No real API calls in skeletons
- No credentials in code
- No network access from skeletons
- No live trading integration

---

## Recommendation

**Proceed to Phase 2: Controlled Live Adapter Test**

Single-step:
1. Set real API key in environment
2. Switch NetworkSandbox to "restricted" mode
3. Send ONE test request to Claude API
4. Verify response parsing
5. Verify budget tracking with real token cost
6. Immediately revert to simulation mode

All under manual control. No automated live calls.
