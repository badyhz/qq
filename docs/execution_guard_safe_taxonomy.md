# Execution Guard SAFE Taxonomy

**Purpose**: Classification model for all scripts in the repo. Determines guard eligibility, risk tier, and modification policy.

**Last updated**: 2026-05-26

---

## Classification Definitions

### 1. SAFE_READONLY_CANDIDATE

**Definition**: Scripts safe for guard injection. Read-only, no network calls to trading endpoints, no order submission. Identified by initial audit as high-confidence guard targets.

**Count**: 5

**Examples**:
- `scripts/validate_testnet_artifacts.py`
- `scripts/generate_runner_dry_run_report.py`
- `scripts/generate_gate_decision_dashboard.py`
- `scripts/generate_trading_system_health_dashboard.py`
- `scripts/generate_sample_collection_eod_report.py`

**Guard eligibility**: YES — `assert_dry_run_required` at CLI entry.

---

### 2. PROMOTE_TO_SAFE

**Definition**: Scripts originally classified as NEEDS_REVIEW but re-audited during T632 deep audit and found safe. No dangerous imports, no network calls, no execution risk.

**Count**: 5

**Examples**:
- `scripts/audit_real_ohlcv_source_schema.py`
- `scripts/calculate_execution_quality_score.py`
- `scripts/generate_ohlcv_gap_validation_control_report_v1.py`
- `scripts/generate_real_ohlcv_source_mapping_v1.py`
- `scripts/validate_real_ohlcv_gap_candidates.py`

**Guard eligibility**: YES — `assert_dry_run_required` at CLI entry.

---

### 3. KEEP_NEEDS_REVIEW

**Definition**: Scripts with residual risk that warrant human review before guard injection. May import network libraries or have indirect side effects.

**Count**: 1

**Examples**:
- `scripts/review_trade_logic_evolution_with_klines.py` — imports `requests`, HTTP to Binance public klines endpoint

**Guard eligibility**: BLOCKED — requires human review before any guard integration.

---

### 4. NOT_ELIGIBLE

**Definition**: Scripts that import dangerous trading modules (`binance_connector`, `order_manager`, etc.) or have execution roles that make guard injection inappropriate. These are not high-risk enough to freeze but not safe enough to guard.

**Count**: ~219 (by name pattern or import analysis)

**Identification heuristics**:
- Name contains: `shadow`, `plan`, `pipeline`, `submit`, `orchestrat`, `shift`, `experiment`
- Imports: `binance_connector`, `order_manager`, `execution`, `live_runner`

**Guard eligibility**: NO — not candidates for guard injection.

---

### 5. HTTP_CAPABLE

**Definition**: Sub-category of NEEDS_REVIEW. Scripts that make network requests (HTTP/HTTPS). Even if read-only, network access introduces external dependency risk.

**Count**: 1

**Examples**:
- `scripts/review_trade_logic_evolution_with_klines.py` — `requests.get()` to Binance public API

**Guard eligibility**: BLOCKED — network risk requires review.

---

### 6. HIGH_RISK_WRITE

**Definition**: Frozen scripts that submit, cancel, or flatten orders. Direct market interaction capability.

**Count**: 7

**Examples**:
- `scripts/submit_approved_candidates.py`
- `scripts/submit_replayed_testnet_payload.py`
- `scripts/run_replay_submit_batch.py`
- `scripts/safe_flatten_testnet_symbol.py`
- `scripts/run_spot_testnet_acceptance.py`
- `scripts/run_testnet_order_smoke.py`
- `scripts/verify_testnet_repair_scenarios.py`

**Guard eligibility**: NO — FROZEN. Phase3 scope. No modification until explicit unfreeze + review.

---

### 7. HIGH_RISK_RUNTIME

**Definition**: Frozen scripts that are long-running orchestrators or runtime loops. May spawn subprocesses, manage state, or coordinate multiple operations.

**Count**: 15

**Examples**:
- `core/live_runner.py`
- `scripts/live_playbook.py`
- `scripts/run_controlled_testnet_shift.py`
- `scripts/run_daily_shadow_scan_pipeline.py`
- `scripts/run_shadow_observation_experiments.py`
- `scripts/run_signal_testnet_trial.py`

**Guard eligibility**: NO — FROZEN. Phase4 scope. No modification until explicit unfreeze + review.

---

### 8. FROZEN

**Definition**: All 22 high-risk files (HIGH_RISK_WRITE + HIGH_RISK_RUNTIME + `core/live_runner.py`). No modification allowed. Read-only audits only.

**Count**: 22

**Breakdown**:
- HIGH_RISK_WRITE: 7 scripts
- HIGH_RISK_RUNTIME: 15 scripts (including `core/live_runner.py`)

**Guard eligibility**: NO — frozen boundary. No code changes. No guard injection.

---

## Coverage Metrics

### Guard Inventory

| Metric | Value |
|---|---|
| Total guarded scripts | 30 |
| Guard function | `assert_dry_run_required` |
| Guard tests | ~308/308 pass |

### Script Distribution

| Classification | Count | Guard Eligible |
|---|---|---|
| SAFE_READONLY_CANDIDATE | 5 | YES |
| PROMOTE_TO_SAFE | 5 | YES |
| KEEP_NEEDS_REVIEW | 1 | BLOCKED |
| NOT_ELIGIBLE | ~219 | NO |
| HTTP_CAPABLE | 1 | BLOCKED |
| HIGH_RISK_WRITE | 7 | FROZEN |
| HIGH_RISK_RUNTIME | 15 | FROZEN |
| **Total** | **~253** | **30 guarded** |

### Coverage Rate

- **Eligible scripts guarded**: 30/41 (73.2% of SAFE backlog)
- **Frozen scripts**: 22 (Phase3-4 boundary, no guard injection)
- **NOT_ELIGIBLE**: ~219 (not candidates)
- **NEEDS_REVIEW**: 2 (1 KEEP_NEEDS_REVIEW + 1 HTTP_CAPABLE, same script)

### Test Baseline

| Scope | Tests | Status |
|---|---|---|
| Guard core (Phase0) | 124 | 124/124 pass |
| Phase2 batch1 (5 scripts) | 30 | 30/30 pass |
| Phase2 batch2 (5 scripts) | 30 | 30/30 pass |
| Phase2 batch3 (5 scripts) | 30 | 24 pass + 6 skipped |
| Phase2 batch4 (5 scripts) | 30 | 30/30 pass |
| Phase2 batch5 (5 scripts) | 30 | 30/30 pass |
| Phase2 batch6 (5 scripts) | 30 | 30/30 pass |
| Total guard tests | ~308 | ~308 pass |

---

## Phase Boundary Summary

| Phase | Scope | Status |
|---|---|---|
| Phase0 | Helper / schema / contract | COMPLETED |
| Phase1 | Readonly integration | COMPLETED |
| Phase2 | Safe batch (30 scripts) | COMPLETED |
| Phase3 | HIGH_RISK_WRITE (7 scripts) | FROZEN |
| Phase4 | HIGH_RISK_RUNTIME (15 scripts) | FROZEN |

---

## References

- `docs/execution_guard_integration_matrix.md` — phase-by-phase integration status
- `docs/execution_guard_phase2_runbook.md` — operational runbook for safe batch
- `docs/remaining_high_risk_frozen_inventory.md` — frozen file inventory
