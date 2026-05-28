# T10701-T13000 Operator Manual / Experiment Library Snapshot

## Snapshot Date
2026-05-28

## release_hold
**HOLD**

## Full Suite Status
7423 passed, 6 skipped, 0 failed

## Tags
| Tag | Description |
|-----|-------------|
| `multi-strategy-research-deep-hardening-complete` | Deep hardening phase |
| `multi-strategy-research-artifact-browser-complete` | Artifact browser |
| `multi-strategy-research-comparison-analytics-complete` | Comparison analytics |
| `multi-strategy-research-human-review-complete` | Human review workflow |

## Documentation Inventory

### Operator Manuals (7)
1. offline_research_stack_operator_manual.md
2. offline_research_stack_quickstart.md
3. offline_research_stack_command_reference.md
4. offline_research_stack_artifact_reference.md
5. offline_research_stack_safety_manual.md
6. offline_research_stack_troubleshooting.md
7. offline_research_stack_faq.md

### Runbooks (13)
Full offline pipeline, quality gate only, artifact browser only, comparison analytics only, human review packet only, reproducibility check, release_hold boundary validation, 3 recovery runbooks, clean outputs, preflight, postflight.

### Checklists (10)
Preflight, postflight, quality gate review, artifact browser review, comparison analytics review, human review signoff, release_hold safety, agent handoff, new experiment intake, final closeout.

### Recovery Docs (9)
Missing artifacts, corrupted JSON, reproducibility mismatch, invalid safety flags, missing review packet, failed full suite, untracked external state, bad commit, restore to tags.

## Experiment Library
- 20 deterministic experiment definitions
- All offline/advisory only
- All with release_hold = HOLD
- 6 invalid fixture files for testing

## Validator Outputs
- experiment_library_validation.json
- governance_validation.json
- governance_validation.md
- governance_manifest.json
- operator_bundle_index.json
- operator_bundle_manifest.json
- operator_bundle.md
- operator_bundle.html
- command_cheatsheet.md
- safety_cheatsheet.md
- recovery_index.md
- experiment_catalog_summary.md

## Safety Boundary
- release_hold = HOLD
- offline only
- advisory only
- human_review_required
- no live/testnet/runtime/planner
- no auto-promotion
- no network
- no exchange

## External Untracked State
Core/live_runner.py, scripts/live_playbook.py, scripts/run_*.py (testnet/shadow), research/ directory remain external state.
