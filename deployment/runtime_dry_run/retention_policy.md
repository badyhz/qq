# Artifact Retention Policy

## Policy Types

| Type | Tracking | Git | Description |
|------|----------|-----|-------------|
| COMMITTED_BASELINE | track | commit | Expected in repo, validated on every run |
| RUNTIME_EPHEMERAL | ignore | ignore | Generated at runtime, gitignored |
| MILESTONE_REPORT | milestone_only | milestone | Generated at milestones, committed manually |
| SAFETY_EVIDENCE | milestone_only | commit | Critical safety proof, committed at milestones |

## Artifact Classification

### COMMITTED_BASELINE (25 artifacts)
- `data/runtime/e2e/run_manifest.json`
- `data/runtime/e2e/system_dry_run_e2e_report.md`
- `data/runtime/e2e/replay_report.json`
- `data/runtime/research/watchlist.jsonl`
- `data/runtime/research/scored_watchlist.jsonl`
- `data/runtime/shadow/signals.jsonl`
- `data/runtime/shadow/shadow_scorecard.json`
- `data/runtime/shadow/promotion_evidence.jsonl`
- `data/runtime/alerts/alerts.jsonl`
- `data/runtime/alerts/feishu_dry_run_payloads.jsonl`
- `data/runtime/alerts/dedup_store.json`
- `data/runtime/operator/system_state.json`
- `data/runtime/operator/dashboard.html`
- `data/runtime/testnet_sim/order_lifecycle.jsonl`
- `data/runtime/testnet_sim/no_submit_evidence.jsonl`
- `data/runtime/observability/runtime_metrics.json`
- `data/runtime/observability/runtime_health.json`
- `data/runtime/safety/no_submit_regression.json`
- `data/runtime/artifacts/artifact_manifest.json`
- `data/runtime/hygiene/artifact_policy.json`
- `data/runtime/hygiene/retention_rules.json`
- `data/runtime/server/environment_check.json`
- `data/runtime/server/systemd_validation.json`
- `data/runtime/server/server_safety.json`
- `data/runtime/testnet_sim/sandbox_gaps.json`

### RUNTIME_EPHEMERAL
- `data/runtime/scheduler/` (scheduled run logs)
- `data/runtime/e2e/isolated/` (isolated E2E runs)

## Implementation

All policies are defined in `src/runtime_integrations/hygiene/runtime_artifact_policy.py`.
Git pollution checking is in `src/runtime_integrations/hygiene/git_pollution_checker.py`.
