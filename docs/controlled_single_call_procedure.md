# Controlled Single Call Procedure

**Date:** 2026-05-27
**Scope:** First real external adapter call
**Status:** PROCEDURE DEFINED — awaiting review board GO

---

## Prerequisites

| # | Requirement | Verified |
|---|---|---|
| 1 | ANTHROPIC_API_KEY set in environment | Config step |
| 2 | NetworkSandbox in "restricted" mode | Config step |
| 3 | "claude_api" on RealAdapterPolicy allowlist | Config step |
| 4 | NETWORK_CALL + REAL_API capabilities registered | Config step |
| 5 | ManualApprovalGate token requested + approved | Config step |
| 6 | PreflightValidator returns PASS | Verified at runtime |
| 7 | Dry-run harness rehearsal completed | Verified by test |

---

## Allowed call types

| Call | Description | Risk |
|---|---|---|
| model_list | List available Claude models | READONLY, no inference |
| health_check | Ping API endpoint | READONLY, minimal tokens |
| tiny_prompt | "Say hello in 5 words" | Low token cost, trivial inference |

## Forbidden

| Action | Reason |
|---|---|
| Workflow run | Not a single call |
| Trading action | Out of scope |
| File mutation | No filesystem writes |
| Live execution | Not approved |
| Multi-turn conversation | Single call only |
| Streaming response | Batch mode only |

---

## Step-by-step sequence

```
Step 1: ENVIRONMENT SETUP
  export ANTHROPIC_API_KEY="sk-ant-..."
  (key never logged, never printed)

Step 2: SWITCH SANDBOX
  NetworkSandbox.set_mode("restricted")
  Verify: api.anthropic.com is on allowlist

Step 3: REGISTER CAPABILITIES
  LiveCapabilityRegistry.register(
    NETWORK_CALL for "claude_api"
    REAL_API for "claude_api"
  )

Step 4: ADD TO ALLOWLIST
  RealAdapterPolicy.add_to_allowlist("claude_api")

Step 5: REQUEST APPROVAL
  ManualApprovalGate.request_approval(
    action="single_health_check",
    adapter_id="claude_api",
    ttl_seconds=300  // 5 minutes only
  )

Step 6: HUMAN APPROVES
  ManualApprovalGate.approve(token)

Step 7: PREFLIGHT
  AdapterPreflightValidator.validate("claude_api")
  Expected: PASS (all 6 checks)

Step 8: RECORD START
  SingleCallRecorder.start_record(...)

Step 9: EXECUTE CALL
  ClaudeAPIAdapter.submit_task("health_check", "Say hello in 5 words")
  ClaudeAPIAdapter.poll(request_id)

Step 10: RECORD END
  SingleCallRecorder.end_record(...)

Step 11: VERIFY
  - Response parsed correctly
  - Budget updated with real token cost
  - Observability events emitted
  - Approval consumed (single-use)

Step 12: REVERT
  NetworkSandbox.set_mode("simulation")
  RealAdapterPolicy.remove_from_allowlist("claude_api")
  LiveCapabilityRegistry.deny(NETWORK_CALL, "claude_api")
  LiveCapabilityRegistry.deny(REAL_API, "claude_api")
```

---

## Rollback

At ANY step, if something unexpected happens:
1. Kill switch: `RealAdapterPolicy.activate_kill_switch()`
2. This immediately blocks ALL adapter requests
3. Revert NetworkSandbox to "simulation"
4. Deny all capabilities
5. Revoke approval token
6. Log the incident

---

## Evidence capture

After the call, capture:
- SingleCallRecord (adapter_id, duration, budget delta, response_status)
- Preflight result (PASS)
- Approval token (consumed)
- Budget before/after
- Observability event timeline

Store in: `logs/first_call_evidence.json`

---

## Success criteria

- [ ] Response received and parsed
- [ ] No errors in preflight
- [ ] Budget updated correctly
- [ ] Approval consumed (single-use enforced)
- [ ] Kill switch testable (activate → blocks)
- [ ] All evidence captured
- [ ] Sandbox reverted to simulation
