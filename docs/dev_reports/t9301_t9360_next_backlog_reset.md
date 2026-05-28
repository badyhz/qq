# T9301-T9360 Next Backlog Reset

Generated: 2026-05-28

## 1. What Not To Do Next

- Do NOT implement live/testnet/runtime features.
- Do NOT touch untracked files (live_runner, shadow scripts, testnet scripts).
- Do NOT lift release_hold.
- Do NOT add exchange clients, network calls, or order placement.
- Do NOT auto-promote research output to live.
- Do NOT modify core strategy behavior.
- Do NOT import from live/testnet/runtime/planner modules.

## 2. Recommended Next Milestones

| ID | Milestone | Category | Risk |
|----|-----------|----------|------|
| T9361 | Documentation consolidation | Docs | Low |
| T9370 | Artifact browser / report UX | Offline tooling | Low |
| T9380 | Research comparison analytics | Offline tooling | Low |
| T9390 | Human review workflow | Offline tooling | Medium |
| T9400 | Test debt / fixture expansion | Testing | Low |

## 3. Safe Task Categories

- Documentation: reports, PRDs, closeout summaries, backlog files
- Offline tooling: artifact browsers, report viewers, comparison dashboards (no network)
- Test infrastructure: new fixtures, adversarial coverage, negative controls
- Utility modules: config loaders, logger enhancements, helper functions (no exchange logic)
- Research analytics: offline comparison, scoring, visualization (advisory only)

## 4. Forbidden Task Categories

- Live trading implementation
- Testnet order submission
- Shadow/live execution runners
- Exchange client integration
- Network-bound data feeds
- Order placement / cancellation / flattening
- Risk manager live enforcement
- Secret/credential management
- Auto-promotion pipelines

## 5. Suggested Next Waves

### Wave A: Documentation Consolidation (T9361-T9365)

- Merge scattered closeout reports into unified index
- Create master timeline document (T4201-T9360)
- Update PROJECT_STATE.md with current phase status
- Standardize report format across all closeout docs

### Wave B: Artifact Browser / Report UX -- Offline Only (T9370-T9375)

- CLI tool to browse research artifacts by date/score/verdict
- Filter by strategy, regime, bootstrap confidence
- Display artifact diff between runs
- All offline, no network, no exchange

### Wave C: Research Comparison Analytics -- Offline Only (T9380-T9385)

- Compare quality gate scores across runs
- Track score trends over time
- Identify regressions in composite score
- Visualize fixture coverage gaps
- All offline, advisory only

### Wave D: Human Review Workflow -- Offline Only (T9390-T9395)

- Structured review checklist for research output
- Approval/rejection workflow with reasons
- Review history tracking
- Integration with existing acceptance.json gates
- No auto-promotion; human decision required

### Wave E: Test Debt / Fixture Expansion (T9400-T9410)

- Add more adversarial fixtures (flash crash, liquidity gap, exchange halt)
- Add more regime fixtures (trend reversal, volatility spike)
- Add more negative control fixtures (mean reversion false positive, momentum decay)
- Improve assertion depth in existing tests
- Target: 50+ fixture files, 150+ adversarial tests

## 6. Parking Lot -- Live/Testnet/Runtime Work, Still Frozen

All items below are **frozen**. Do not implement until explicit human approval lifts the freeze.

| Item | Status | Untracked File |
|------|--------|----------------|
| Live runner | Frozen | `core/live_runner.py` |
| Live playbook | Frozen | `scripts/live_playbook.py` |
| Shadow observation | Frozen | `scripts/run_shadow_observation_experiments.py` |
| Shadow sample collection | Frozen | `scripts/run_shadow_sample_collection_pipeline.py` |
| Shadow universe collector | Frozen | `scripts/run_shadow_universe_collector.py` |
| Shadow scan pipeline | Frozen | `scripts/run_daily_shadow_scan_pipeline.py` |
| Shadow experiment plan | Frozen | `scripts/run_next_shadow_experiment_plan.py` |
| Observation shift runtime | Frozen | `scripts/run_observation_shift_runtime.py` |
| Remediation loop | Frozen | `scripts/run_remediation_shadow_only_loop.py` |
| Testnet order smoke | Frozen | `scripts/run_testnet_order_smoke.py` |
| Testnet trial | Frozen | `scripts/run_signal_testnet_trial.py` |
| Testnet acceptance | Frozen | `scripts/run_spot_testnet_acceptance.py` |
| Testnet repair | Frozen | `scripts/verify_testnet_repair_scenarios.py` |
| Testnet flatten | Frozen | `scripts/safe_flatten_testnet_symbol.py` |
| Controlled testnet shift | Frozen | `scripts/run_controlled_testnet_shift.py` |
| Submit candidates | Frozen | `scripts/submit_approved_candidates.py` |
| Replay submit | Frozen | `scripts/submit_replayed_testnet_payload.py` |
| Replay shadow plans | Frozen | `scripts/replay_shadow_order_plans_as_testnet_dry.py` |
| Risk release flow | Frozen | `scripts/verify_risk_release_flow.py` |
| Right breakout scan | Frozen | `scripts/run_right_breakout_scan_dry.py` |
| Right breakout param | Frozen | `scripts/run_right_breakout_param_observation.py` |
| Research directory | Frozen | `research/` |

**Rule:** These files exist in the working tree as external state. Never stage, import, execute, delete, or rename them.

## 7. Prompt Template for Next Claude Window

```
You are working on the qq quantitative trading system.

Current state:
- HEAD: 7eea90d (or later)
- Phase: Research workbench closeout complete
- release_hold: HOLD
- advisory_only: True
- human_review_required: True

Task: [INSERT TASK FROM WAVES A-E ABOVE]

Rules:
1. Read PROJECT_STATE.md, TASKS.md, acceptance.json, feature_list.json, AGENT_RULES.md first
2. Never git add .
3. Never touch untracked files
4. Never import live/testnet/runtime/planner/exchange modules
5. Research output is advisory only
6. release_hold must remain HOLD
7. All work is offline only -- no network, no exchange, no order placement
8. Update control files after implementation

Safety check before any change:
- release_hold == HOLD?
- advisory_only == True?
- human_review_required == True?
- No frozen files touched?
- No untracked files staged?
```
