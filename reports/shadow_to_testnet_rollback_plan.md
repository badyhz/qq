# Shadow-to-Testnet Rollback Plan

**Plan ID:** shadow_to_testnet_rollback_plan
**Total steps:** 5
**simulation_only:** True
**release_hold:** HOLD

## Trigger Conditions

- testnet_dry_run_submits_real_order
- no_submit_guard_bypassed
- critical_blocker_detected
- stability_score_below_threshold
- human_operator_requests_rollback

## Rollback Steps

### Step 1: REVERT_TO_SHADOW_ONLY

- **step_id:** rollback_1
- **description:** Revert system mode to SHADOW_ONLY
- **simulation_only:** True

### Step 2: DISABLE_TESTNET_DRY_RUN

- **step_id:** rollback_2
- **description:** Disable testnet dry-run orchestrator
- **simulation_only:** True

### Step 3: RE_ENABLE_NO_SUBMIT_GUARD

- **step_id:** rollback_3
- **description:** Re-enable no-submit execution guard
- **simulation_only:** True

### Step 4: RESTORE_FROZEN_STATE

- **step_id:** rollback_4
- **description:** Restore all frozen files to pre-promotion state
- **simulation_only:** True

### Step 5: GENERATE_ROLLBACK_REPORT

- **step_id:** rollback_5
- **description:** Generate rollback evidence report
- **simulation_only:** True

---
ROLLBACK PLAN. SIMULATION ONLY. NO REAL ACTIONS.
