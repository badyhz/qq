# Phase3 Research Lab

## Status: RESEARCH ONLY -- NO IMPLEMENTATION

## Research Questions

1. What changes in runtime integration?
2. What changes in planner integration?
3. What new guard contracts are required?
4. What rollback strategy is needed?
5. What new governance risks appear?

---

## Guard Contract Analysis

### Existing Guards (Phase0)

| Guard | Signature | Phase2 Usage | Phase3 Usage |
|-------|-----------|-------------|-------------|
| `assert_dry_run_required(mode)` | `(mode: str \| None) -> str` | 41 scripts | N/A (read-only scripts) |
| `assert_submit_unlocked(...)` | 6-layer unlock, keyword-only | unused | 5 scripts |
| `assert_flatten_unlocked(...)` | 6-layer unlock, keyword-only | unused | 1 script |
| `assert_cancel_unlocked(...)` | 6-layer unlock, keyword-only | unused | 1 script |
| `assert_no_live_mode(mode)` | `(mode: str \| None) -> str` | unused | unused |

### Phase3 Guard Mapping

| Script | Required Guard | Kill-Switch | Action Type |
|--------|----------------|-------------|-------------|
| submit_approved_candidates.py | `assert_submit_unlocked` | `QQ_NO_SUBMIT` | entry order submission |
| submit_replayed_testnet_payload.py | `assert_submit_unlocked` | `QQ_NO_SUBMIT` | entry + protective order submission |
| run_replay_submit_batch.py | `assert_submit_unlocked` | `QQ_NO_SUBMIT` | batch entry submission |
| safe_flatten_testnet_symbol.py | `assert_flatten_unlocked` | `QQ_NO_FLATTEN` | position close + cancel protective orders |
| run_spot_testnet_acceptance.py | `assert_submit_unlocked` | `QQ_NO_SUBMIT` | spot testnet order submission |
| run_testnet_order_smoke.py | `assert_submit_unlocked` | `QQ_NO_SUBMIT` | testnet order submission + cancel |
| verify_testnet_repair_scenarios.py | `assert_cancel_unlocked` | `QQ_NO_CANCEL` | cancel orphan protective orders |

### Guard Function Signatures (Actual)

```python
# From core/execution_guards.py — full 6-layer unlock assertions
def assert_submit_unlocked(
    *,
    mode: str | None,
    symbol: str = "",
    symbol_allowlist: frozenset[str] = frozenset(),
    capability: bool = False,
    cli_allow: bool = False,
    manual_confirm: bool = False,
) -> str:
    """Layer0: QQ_NO_SUBMIT kill-switch, Layer1-5: unlock gates. Returns normalized mode."""

def assert_flatten_unlocked(
    *,
    mode: str | None,
    symbol: str = "",
    symbol_allowlist: frozenset[str] = frozenset(),
    capability: bool = False,
    cli_allow: bool = False,
    manual_confirm: bool = False,
) -> str:
    """Layer0: QQ_NO_FLATTEN kill-switch, Layer1-5: unlock gates. Returns normalized mode."""

def assert_cancel_unlocked(
    *,
    mode: str | None,
    symbol: str = "",
    symbol_allowlist: frozenset[str] = frozenset(),
    capability: bool = False,
    cli_allow: bool = False,
    manual_confirm: bool = False,
) -> str:
    """Layer0: QQ_NO_CANCEL kill-switch, Layer1-5: unlock gates. Returns normalized mode."""
```

### Critical Observation

The existing guard functions are **not** simple kill-switch checks. They are full 6-layer unlock assertions requiring: mode, symbol, symbol_allowlist, capability flag, cli_allow flag, and manual_confirm. This means Phase3 integration must either:

1. Pass all 6 layers to the existing guards, or
2. Create simplified wrappers for scripts that do not need full layered unlock

---

## Per-Script Analysis

### 1. submit_approved_candidates.py (1053 lines)

**Purpose:** Bridge approved execution candidates into the testnet replay batch runner.

**Current safety layers (NO execution guard):**
- Live env blocked via risk event logging (line 486-502)
- Account risk guard via `validate_account_risk_before_submit` (line 638)
- Strategy gate via `pre_submit_strategy_gate` (line 553)
- Preflight state checks (FLAT_CLEAN / FULLY_PROTECTED / NAKED_POSITION)
- Symbol allowlist enforcement
- Dry-run default (dry_run=True)

**Guard integration point:** Top of `submit_approved_candidates()` function, before any candidate processing.

**Challenge:** The function signature already has `dry_run: bool = True` and `allow_testnet_submit: bool = False`. Guard must respect existing mode logic. The 6-layer guard requires `capability`, `cli_allow`, and `manual_confirm` flags -- these do not currently exist in the function signature.

**Call chain:** `submit_approved_candidates` -> `run_replay_submit_batch` -> `submit_replayed_testnet_payloads`. Guard at top of `submit_approved_candidates` would protect the entire chain, but a bypass at the `run_replay_submit_batch` level (called directly) would not be caught.

**Dependencies:** Imports `run_replay_submit_batch`, `check_testnet_state`, `pre_submit_strategy_gate`, `generate_testnet_acceptance_report`, `execution_candidate_queue`, `account_risk_guard`, `risk_event_logger`.

---

### 2. submit_replayed_testnet_payload.py (1231 lines)

**Purpose:** Core submit logic -- submit replayed testnet dry payloads to Binance futures testnet.

**Current safety layers (NO execution guard):**
- Env testnet check via risk event (line 601-609)
- Execution safety via `validate_execution_safety` (line 633-649)
- API auth check before submit (line 717-731)
- Symbol allowlist enforcement
- Preflight protection state checks
- max_submit_orders=1 hard limit
- submit_eligible, precision_status, quantity_status, notional checks

**Guard integration point:** Top of `submit_replayed_testnet_payloads()` function.

**Challenge:** This is the inner-most submit function called by batch runner and approved candidates. Guard here protects the actual order placement. The function is also imported by other Phase3 scripts (`run_replay_submit_batch`, `safe_flatten_testnet_symbol`, `verify_testnet_repair_scenarios`).

**Dependencies:** Imports `BinanceFuturesTestnetClient`, `execution_safety`, `risk_event_logger`, `trade_logger`.

---

### 3. run_replay_submit_batch.py (491 lines)

**Purpose:** Batch runner -- submit multiple symbols' replayed payloads in sequence.

**Current safety layers (NO execution guard):**
- Env testnet check via risk event (line 114-138)
- Execution safety via `validate_execution_safety` (line 107-113)
- Account risk guard per symbol (line 303-341)
- Preflight state checks per symbol
- Symbol allowlist enforcement

**Guard integration point:** Top of `run_replay_submit_batch()` function, before symbol iteration.

**Challenge:** This script is called by `submit_approved_candidates` AND can be invoked directly from CLI. Guard at top protects both paths.

**Dependencies:** Imports `submit_replayed_testnet_payloads`, `check_testnet_state`, `account_risk_guard`, `risk_event_logger`, `trade_logger`.

---

### 4. safe_flatten_testnet_symbol.py (338 lines)

**Purpose:** Safely flatten one Binance futures testnet symbol (cancel protective orders + close position).

**Current safety layers (NO execution guard):**
- Env testnet check via risk event (line 98-117)
- Execution safety via `validate_execution_safety` (line 164-171)
- confirm + dry_run dual flag enforcement
- Risk event logging for all operations

**Guard integration point:** Top of `safe_flatten_testnet_symbol()` function, before any operation.

**Challenge:** This script performs BOTH cancel (protective orders) AND close (position) operations. It needs `assert_flatten_unlocked` for position close, but may also need `assert_cancel_unlocked` for cancel operations. The flatten guard is the primary gate.

**Dependencies:** Imports `BinanceFuturesTestnetClient`, `execution_safety`, `risk_event_logger`, `submit_replayed_testnet_payload` (for helpers).

---

### 5. run_spot_testnet_acceptance.py (154 lines)

**Purpose:** One-click Spot testnet stage-1 acceptance checks (order submit + status query + cancel).

**Current safety layers (NO execution guard):**
- Env testnet/sandbox check (line 63-87)
- Uses `_NoopExchange` (never actually enables live exchange)
- Acceptance check flow: submit -> status query -> cancel

**Guard integration point:** Top of `run_spot_testnet_acceptance_bundle()` function.

**Challenge:** This is the simplest script. It uses `ExecutionEngine` which may internally handle some safety. The `_NoopExchange` means orders go through the broker connector, not the exchange directly.

**Dependencies:** Imports `BinanceConnector`, `ExecutionEngine`, `OrderManager`.

---

### 6. run_testnet_order_smoke.py (268 lines)

**Purpose:** Run testnet order smoke with strict gate checks (submit + status query + cancel + review).

**Current safety layers (NO execution guard):**
- Mode-based connector building (dry-run mode returns None connector)
- ExecutionEngine handles safety internally

**Guard integration point:** Top of `run_testnet_order_smoke_bundle()` function.

**Challenge:** Accepts `mode` parameter ("dry-run", "testnet", "live"). Guard must validate mode before any operation. When mode="testnet", `effective_live_trading` is forced True (line 210).

**Dependencies:** Imports `BinanceConnector`, `ExecutionEngine`, `OrderManager`.

---

### 7. verify_testnet_repair_scenarios.py (306 lines)

**Purpose:** Verify testnet repair scenarios (diagnose + dry plan only by default).

**Current safety layers (NO execution guard):**
- Env testnet check (line 94-102)
- dry_run always True in CLI (line 278: `True if bool(args.dry_run) else True`)
- No actual order submission in default mode

**Guard integration point:** Top of `verify_testnet_repair_scenarios()` function.

**Challenge:** This script is diagnostic-only in default mode. However, the `repair_protective_orders` and `cleanup_orphan_protective_orders` flags can enable real actions (though currently the function only plans, does not execute). The governance board requires `assert_cancel_unlocked` because planned actions include `cancel_orphan_algo_orders`.

**Dependencies:** Imports `BinanceFuturesTestnetClient`, `submit_replayed_testnet_payload` (for helpers).

---

## Runtime Integration Changes

### Current State (Phase2)
- Guard at CLI entry only (assert_dry_run_required in 41 scripts)
- No runtime integration
- No live_runner modifications
- Guard called once per script execution

### Phase3 Requirements
- Guard must be called before each submit/cancel/flatten operation
- Guard must be called at function entry (not just CLI entry)
- Guard must work with 6-layer unlock parameters
- Guard must not break existing safety layers

### Key Differences

| Aspect | Phase2 | Phase3 |
|--------|--------|--------|
| Guard location | CLI entry (main) | Function entry (core logic) |
| Guard frequency | Once per run | Once per call site |
| Guard type | Simple mode check | Full 6-layer unlock |
| Parameters | mode only | mode, symbol, allowlist, capability, cli_allow, confirm |
| Failure mode | Script exits | Operation blocked, error returned |
| Existing safety | N/A | Must coexist with execution_safety, account_risk_guard, preflight checks |

### Guard Coexistence Strategy

Phase3 scripts already have multiple safety layers. The execution guard adds a kill-switch layer on top. The recommended approach is:

1. **Layer 0 (kill-switch):** Check `QQ_NO_SUBMIT` / `QQ_NO_FLATTEN` / `QQ_NO_CANCEL` at function entry
2. **Layers 1-5 (unlock):** Only enforce if the script is being called in a context where the operator intends to perform real operations

This means the guard call should be conditional on `effective_allow_submit` or equivalent, not unconditional. Otherwise, dry-run invocations would be blocked by Layer1 (capability) and Layer3 (env unlock).

---

## Planner Integration Changes

### Current State (Phase2)
- No planner integration
- Planner path frozen
- Strategy gate exists but is read-only by default

### Phase3 Requirements
- Guard status should be reflected in gate decisions
- Guard should not interfere with strategy gate logic
- Guard status should be recorded in audit manifests

### Key Differences

| Aspect | Phase2 | Phase3 |
|--------|--------|--------|
| Planner involvement | None | Pre-submit check (indirect) |
| Strategy gate | Read-only | Could block based on guard status |
| Audit trail | None | Guard status in manifest |

---

## New Guard Contracts Required

### Analysis: Do new contracts exist, or do we use existing ones?

The existing guard functions (`assert_submit_unlocked`, `assert_flatten_unlocked`, `assert_cancel_unlocked`) already provide the full 6-layer unlock logic. No new guard contracts are strictly required for Phase3.

However, convenience wrappers would simplify integration:

### 1. Kill-Switch-Only Wrapper (Recommended)

```python
def assert_submit_killswitch() -> None:
    """Check only Layer0 (QQ_NO_SUBMIT kill-switch). Suitable for scripts
    that do not need full 6-layer unlock."""
    if read_bool_env("QQ_NO_SUBMIT"):
        raise ExecutionGuardError("submit blocked by QQ_NO_SUBMIT")
```

This is the simplest integration path. Phase3 scripts already have their own safety layers (execution_safety, account_risk_guard, preflight checks). Adding the kill-switch-only check at function entry provides a fast-fail mechanism without requiring all 6 layers.

### 2. Full 6-Layer Wrapper (If needed later)

The existing `assert_submit_unlocked`, `assert_flatten_unlocked`, `assert_cancel_unlocked` already serve this purpose.

### 3. Runtime Guard Report

```python
def generate_runtime_guard_report() -> dict:
    """Generate guard status report for runtime monitoring."""
    return {
        "submit_allowed": not read_bool_env("QQ_NO_SUBMIT"),
        "flatten_allowed": not read_bool_env("QQ_NO_FLATTEN"),
        "cancel_allowed": not read_bool_env("QQ_NO_CANCEL"),
        "live_allowed": not read_bool_env("QQ_NO_LIVE"),
        "dry_run_required": read_bool_env("QQ_REQUIRE_DRY_RUN"),
    }
```

This exists implicitly in the schema/status report but could be called at runtime for monitoring.

---

## Rollback Strategy

### Per-Script Rollback

Each Phase3 script needs:
1. Pre-guard commit hash documented
2. Guard injection commit (single commit per script or batch)
3. Rollback command documented

### Rollback Commands

```bash
# Rollback single script
git checkout {pre-guard-commit} -- scripts/{script}.py

# Rollback all Phase3
git checkout {pre-phase3-commit} -- scripts/submit_approved_candidates.py \
  scripts/submit_replayed_testnet_payload.py \
  scripts/run_replay_submit_batch.py \
  scripts/safe_flatten_testnet_symbol.py \
  scripts/run_spot_testnet_acceptance.py \
  scripts/run_testnet_order_smoke.py \
  scripts/verify_testnet_repair_scenarios.py

# Full rollback to Phase2
git tag -l "phase2*"  # find the tag
git checkout phase2-complete -- scripts/
```

### Rollback Verification

```bash
# Verify rollback
git diff phase2-complete -- scripts/{script}.py
# Should show no changes

# Verify guard still works after rollback
python -c "from core.execution_guards import read_bool_env; print(read_bool_env('QQ_NO_SUBMIT'))"
```

---

## New Governance Risks

### 1. Accidental Live Order
- **Risk:** Guard bypass leads to real money loss
- **Mitigation:** `QQ_NO_SUBMIT` kill-switch, testnet-first validation, `execution_safety` layer
- **Detection:** Runtime monitoring, order logging, risk event logging
- **Severity:** CRITICAL

### 2. Partial Fill Handling
- **Risk:** Order submitted, guard activated mid-fill
- **Mitigation:** Atomic guard check before submission (fail-closed design)
- **Detection:** Fill monitoring, position reconciliation
- **Severity:** HIGH

### 3. Subprocess Bypass
- **Risk:** Child process bypasses parent guard
- **Mitigation:** Environment variable inheritance, subprocess guard call
- **Detection:** Process monitoring
- **Severity:** MEDIUM (Phase3 scripts do not spawn subprocesses for order placement)

### 4. Rollback Complexity
- **Risk:** Partial rollback leaves inconsistent state
- **Mitigation:** Atomic rollback per script, full regression after rollback
- **Detection:** State verification, test suite
- **Severity:** HIGH

### 5. Multi-Script Coordination
- **Risk:** Scripts depend on each other's guard state (submit_approved_candidates calls run_replay_submit_batch)
- **Mitigation:** Guard at each function entry point, not just top-level caller
- **Detection:** Integration testing, call chain analysis
- **Severity:** MEDIUM

### 6. Guard Parameter Complexity
- **Risk:** 6-layer unlock requires capability, cli_allow, manual_confirm flags that scripts don't currently have
- **Mitigation:** Use kill-switch-only wrappers initially; add full 6-layer later if needed
- **Detection:** Guard test coverage per script
- **Severity:** HIGH (integration complexity)

### 7. Dual Guard Paths
- **Risk:** `safe_flatten_testnet_symbol` performs both cancel and close operations -- which guard applies?
- **Mitigation:** Use `assert_flatten_unlocked` as primary; document that flatten implies cancel authority
- **Detection:** Test both paths
- **Severity:** MEDIUM

---

## Go/No-Go Checklist

### Prerequisites (ALL must be YES)

- [ ] Phase2 tag exists and points to HEAD
- [ ] Phase2 regression clean (124/124)
- [ ] Phase2 coverage 100% (41/41)
- [ ] Guard functions implemented and tested (assert_submit_unlocked, assert_flatten_unlocked, assert_cancel_unlocked)
- [ ] Kill-switch coverage verified per script
- [ ] Each target script reviewed individually
- [ ] Rollback plan documented per script
- [ ] Unfreeze decision recorded in PROJECT_STATE.md
- [ ] Governance board updated

### Risk Assessment

| Risk | Severity | Mitigation | Acceptable? |
|------|----------|------------|-------------|
| Accidental live order | CRITICAL | QQ_NO_SUBMIT + execution_safety | Must be YES |
| Partial fill | HIGH | Atomic guard (fail-closed) | Must be YES |
| Guard parameter complexity | HIGH | Kill-switch-only wrappers | Must be YES |
| Rollback complexity | HIGH | Per-script rollback | Must be YES |
| Multi-script coordination | MEDIUM | Guard at each entry point | Must be YES |
| Subprocess bypass | MEDIUM | Not applicable (no subprocess orders) | YES |
| Dual guard paths | MEDIUM | Flatten = cancel authority | Must be YES |

### Go/No-Go Decision

- **GO:** All prerequisites YES, all risks mitigated
- **NO-GO:** Any prerequisite NO, any risk unacceptable

---

## Integration Approach Options

### Option A: Kill-Switch Only (Recommended for Phase3)

Add `assert_submit_killswitch()` / `assert_flatten_killswitch()` / `assert_cancel_killswitch()` at each function entry. These check only Layer0 (QQ_NO_* env var). Simple, low-risk, preserves existing safety layers.

**Pros:** Minimal code change, no parameter threading, coexists with existing safety.
**Cons:** Does not enforce Layers 1-5 (capability, cli_allow, manual_confirm).

### Option B: Full 6-Layer at Function Entry

Thread `mode`, `symbol`, `symbol_allowlist`, `capability`, `cli_allow`, `manual_confirm` through function signatures.

**Pros:** Full guard enforcement.
**Cons:** High integration complexity, requires signature changes across 7 scripts, breaks existing callers.

### Option C: Full 6-Layer at CLI Entry Only

Add guard at CLI `main()` function entry, before calling core functions.

**Pros:** Centralized, minimal function signature changes.
**Cons:** Does not protect direct function imports (e.g., `submit_replayed_testnet_payloads` imported by batch runner).

**Recommendation:** Option A (kill-switch only) for Phase3. Option B can be added in a future phase if needed.

---

## Recommended Batch Structure

### Batch 1: Submit Scripts (3 scripts)
1. `submit_replayed_testnet_payload.py` -- inner-most submit, guard here protects all callers
2. `run_replay_submit_batch.py` -- batch runner, calls submit_replayed_testnet_payloads
3. `submit_approved_candidates.py` -- top-level orchestrator, calls run_replay_submit_batch

**Rationale:** These form a call chain. Guard at each level provides defense-in-depth.

### Batch 2: Non-Submit Scripts (4 scripts)
4. `safe_flatten_testnet_symbol.py` -- flatten (cancel + close)
5. `run_spot_testnet_acceptance.py` -- spot testnet acceptance
6. `run_testnet_order_smoke.py` -- testnet order smoke
7. `verify_testnet_repair_scenarios.py` -- repair scenario diagnostics

**Rationale:** Independent scripts, simpler integration.

---

## Estimated Effort

| Metric | Estimate |
|--------|----------|
| Scripts to modify | 7 |
| Lines of change per script | 5-15 (guard call + import) |
| Total lines of change | ~50-100 |
| Test additions per script | 6 (matching Phase2 pattern) |
| Total new tests | ~42 |
| Batches | 2 |
| Estimated risk | MEDIUM-HIGH (vs LOW for Phase2) |
| Key difference | Runtime function entry, not just CLI entry |

---

## Summary

Phase3 requires adding execution guard calls at function entry points in 7 frozen HIGH_RISK_WRITE scripts. Unlike Phase2 (which added `assert_dry_run_required` at CLI entry), Phase3 operates at the function level where orders are actually placed. The existing 6-layer guard functions are available but their full parameter requirements (capability, cli_allow, manual_confirm) create integration complexity. A kill-switch-only approach (Layer0 only) is recommended for Phase3, with full 6-layer enforcement deferred to a future phase. All 7 scripts already have significant safety layers (execution_safety, account_risk_guard, preflight checks) that would remain intact. The execution guard adds a global kill-switch on top.
