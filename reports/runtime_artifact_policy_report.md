# Runtime Artifact Hygiene Policy

| Pattern | Category | Git Action |
|---------|----------|------------|
| data/runtime/e2e/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/shadow/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/alerts/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/testnet_sim/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/operator/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/research/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/replay/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/scenarios/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/artifacts/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/observability/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/safety/* | SAFETY_EVIDENCE | milestone_only |
| data/runtime/hygiene/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/scheduler/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/server/* | RUNTIME_EPHEMERAL | ignore |
| data/runtime/stabilization/* | MILESTONE_REPORT | milestone_only |
| data/runtime/final_stabilization/* | MILESTONE_REPORT | milestone_only |
| reports/operator_dashboard.html | RUNTIME_EPHEMERAL | ignore |
| reports/system_dry_run_e2e_report.md | RUNTIME_EPHEMERAL | ignore |
| reports/runtime_*.md | RUNTIME_EPHEMERAL | ignore |
| reports/final_*.md | MILESTONE_REPORT | milestone_only |
| reports/server_*.md | RUNTIME_EPHEMERAL | ignore |
| deployment/runtime_dry_run/* | COMMITTED_BASELINE | track |
| src/runtime_integrations/** | COMMITTED_BASELINE | track |
| tests/integration/** | COMMITTED_BASELINE | track |
| scripts/run_*.py | COMMITTED_BASELINE | track |

## Rules

- RUNTIME_EPHEMERAL: gitignore, regenerated each run
- SAFETY_EVIDENCE: commit at milestones only
- MILESTONE_REPORT: commit at milestones only
- COMMITTED_BASELINE: always track
