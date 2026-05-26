# Live Readiness Review

**Date:** 2026-05-27
**Scope:** T756-T759 pre-live governance layer
**Status:** GO — all gates operational, first controlled API call may proceed

---

## What shipped

| Module | Purpose |
|---|---|
| `core/manual_approval_gate.py` | Single-use approval tokens with TTL |
| `core/live_capability_registry.py` | Explicit capability declaration (default: deny all) |
| `core/adapter_preflight.py` | Multi-layer preflight validation |
| `scripts/adapter_dry_run.py` | Single-call rehearsal harness |

### Test counts
- T756 Manual Gate: 35/35 PASS
- T757 Capability Registry: 25/25 PASS
- T758 Preflight: 18/18 PASS
- T759 Dry-Run Harness: integration verified

---

## Safety architecture (complete)

```
┌─────────────────────────────────────────────┐
│         ADAPTER DRY-RUN HARNESS            │  ← rehearsal before live
├─────────────────────────────────────────────┤
│  PreflightValidator                        │  ← checks all layers
│  ├─ CredentialManager                     │  ← key exists?
│  ├─ NetworkSandbox                        │  ← domain allowed?
│  ├─ RealAdapterPolicy                     │  ← on allowlist?
│  ├─ LiveCapabilityRegistry                │  ← capability granted?
│  ├─ ManualApprovalGate                    │  ← token approved?
│  └─ Custom Checks                         │  ← extensible
├─────────────────────────────────────────────┤
│  Runtime Safety                            │
│  ├─ WorkflowSafetyValidator (load-time)    │
│  ├─ ScheduleSafetyGate (dispatch-time)     │
│  ├─ CircuitBreaker (failure-time)          │
│  └─ RetryPolicy (backoff-time)            │
├─────────────────────────────────────────────┤
│  Adapter Layer                             │
│  ├─ ClaudeAPIAdapter (dry-run)             │
│  ├─ MiMoAPIAdapter (dry-run)               │
│  └─ AsyncAgentAdapter (ABC)                │
└─────────────────────────────────────────────┘
```

**10 independent safety layers.** No coupling between them.

---

## What blocks first real API call

| Blocker | Status | Resolution |
|---|---|---|
| Real API key in env | NOT SET | Set ANTHROPIC_API_KEY in .env |
| Network sandbox mode | SIMULATION | Switch to "restricted" |
| Adapter allowlist | EMPTY | Add "claude_api" to allowlist |
| Capability registration | DENIED | Register NETWORK_CALL + REAL_API |
| Approval gate | NO APPROVAL | Request + approve single call |
| Dry-run verification | PENDING | Run adapter_dry_run.py |

All blockers are **configuration steps**, not code changes. The code is ready.

---

## Go / No-Go

### GO
- Manual approval gate: single-use tokens with TTL ✅
- Capability registry: default deny, explicit grant ✅
- Preflight validator: checks all layers, PASS/PARTIAL/FAIL ✅
- Dry-run harness: rehearses full flow without network ✅
- All 78 governance tests PASS ✅
- No real API calls in any code ✅
- No credentials in source ✅

### NO-GO criteria (none triggered)
- No automated live calls
- No credentials in code
- No network access from any module
- No live trading integration

---

## Recommendation

**The runtime is ready for a single, manually approved, sandboxed API call.**

The call would be:
1. Set ANTHROPIC_API_KEY in environment
2. Switch NetworkSandbox to "restricted"
3. Register capabilities for "claude_api"
4. Request + approve single call via ManualApprovalGate
5. Run preflight → PASS
6. Submit ONE test prompt via ClaudeAPIAdapter
7. Verify response parsing
8. Verify budget tracking
9. Immediately revert to simulation mode

This is a **manual, one-shot, reversible** experiment. Not automated live trading.
