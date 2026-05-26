# First Real Adapter Call — Review Board

**Date:** 2026-05-27
**Scope:** GO / NO-GO for first controlled external API call
**Status:** **GO — CONDITIONAL**

---

## Checklist evaluation

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Procedure exists | ✅ | `docs/controlled_single_call_procedure.md` |
| 2 | Recorder exists | ✅ | `core/single_call_recorder.py` (12 tests) |
| 3 | Kill switch drill passes | ✅ | `test_kill_switch_drill.py` (16/16 PASS) |
| 4 | Credential isolation exists | ✅ | `core/credential_manager.py` (30 tests) |
| 5 | Network sandbox exists | ✅ | `core/network_sandbox.py` (24 tests) |
| 6 | Manual approval exists | ✅ | `core/manual_approval_gate.py` (35 tests) |
| 7 | Capability registry exists | ✅ | `core/live_capability_registry.py` (25 tests) |
| 8 | Budget tracking exists | ✅ | `core/workflow_budget.py` + `runtime_budget_attribution.py` |
| 9 | Circuit breaker exists | ✅ | `core/workflow_circuit_breaker.py` |
| 10 | Retry policy exists | ✅ | `core/workflow_retry_policy.py` |
| 11 | Observability exists | ✅ | `core/workflow_observability.py` |
| 12 | Preflight validator exists | ✅ | `core/adapter_preflight.py` (18 tests) |
| 13 | API skeleton exists | ✅ | `adapters/claude_api_adapter.py` (24 tests) |
| 14 | Dry-run harness exists | ✅ | `scripts/adapter_dry_run.py` (15 tests) |

**14/14 checks PASS**

---

## Decision: **GO — CONDITIONAL**

### Rationale
All 10 safety layers are operational. All code tests pass. The procedure is defined. The kill switch drill validates revocation scenarios. The only remaining steps are configuration (env var, mode switch, allowlist, capability grant, approval token).

### Conditions for GO
1. Human must set ANTHROPIC_API_KEY in environment (not in code)
2. Human must approve the single call via ManualApprovalGate
3. NetworkSandbox must be switched to "restricted" mode
4. Capabilities must be explicitly registered
5. Adapter must be added to allowlist
6. After call: immediately revert to simulation mode

---

## Allowed first call candidate

```
Adapter:    ClaudeAPIAdapter
Call type:  model_list (list available models)
Endpoint:   GET /v1/models
Risk:       READONLY — no inference, no token cost
Duration:   < 2 seconds expected
Budget:     ~$0.00 (no inference tokens)
```

### Why model_list
- Zero inference cost (metadata endpoint)
- Validates auth works
- Validates response parsing works
- Validates budget tracking works
- Lowest possible risk

### Alternative (if model_list not available)
```
Call type:  tiny_prompt
Prompt:     "Say hello in 5 words"
Risk:       Trivial inference, ~10 tokens
Budget:     < $0.001
```

---

## Exact blockers

| # | Blocker | Type | Resolution |
|---|---|---|---|
| 1 | No API key in env | Config | `export ANTHROPIC_API_KEY=...` |
| 2 | Sandbox in simulation mode | Config | Switch to "restricted" |
| 3 | Adapter not on allowlist | Config | Add "claude_api" |
| 4 | Capabilities not registered | Config | Register NETWORK_CALL + REAL_API |
| 5 | No approval token | Config | Request + approve |
| 6 | Preflight not run | Runtime | Run preflight → expect PASS |

**All blockers are configuration, not code.**

---

## Human approval checklist

Before executing first call, confirm:

- [ ] I have set ANTHROPIC_API_KEY in my environment
- [ ] I understand this is a ONE-TIME, REVERSIBLE experiment
- [ ] I have reviewed the procedure in `docs/controlled_single_call_procedure.md`
- [ ] I approve a single model_list or health_check call to api.anthropic.com
- [ ] I will revert to simulation mode immediately after
- [ ] I accept responsibility for this experimental call

---

## Post-call actions

1. Verify response was parsed correctly
2. Check budget tracking recorded real token cost
3. Verify approval token was consumed (single-use)
4. Revert NetworkSandbox to "simulation"
5. Remove adapter from allowlist
6. Deny all capabilities
7. Store evidence in `logs/first_call_evidence.json`
8. Document results

---

## Summary

The runtime stack is complete. 10 safety layers operational. All code tests pass. The procedure is defined. The kill switch drill validates emergency stop.

**The only thing between now and first real API call is human configuration + approval.**

This is by design.
