# Final Untracked Cleanup Preview After 4ffabe2

**Date:** 2026-06-16
**Status:** PREVIEW ONLY - no `rm`, no `git clean`, no `git add`, no commit, no push
**Baseline:** `4ffabe2 Add MACD rebound signal plugin`

## Current Untracked Inventory

`git ls-files --others --exclude-standard` reports **1931** untracked paths before this preview document was created.

`git status --short` reports fewer lines because it can collapse some untracked directory display. Use `git ls-files --others --exclude-standard` for exact cleanup inventory.

## Classification

| Category | Count | Decision |
|----------|------:|----------|
| MUST_KEEP_ALREADY_COMMITTED_RELATED | 0 | none |
| DOCS_REVIEW_KEEP_CANDIDATE | 11 | keep candidate |
| GENERATED_SAFETY_JUNK_DROP_CANDIDATE | 1899 | drop candidate after explicit authorization |
| LOCAL_HOLD | 13 | hold |
| UNKNOWN_NEEDS_REVIEW | 8 | manual review |

## MUST_KEEP_ALREADY_COMMITTED_RELATED

```text
none
```

The risk manager and MACD plugin work is already committed in `e407cb3` and `4ffabe2`.

## DOCS_REVIEW_KEEP_CANDIDATE

```text
docs/FINAL_GIT_STATUS_REVIEW_2026-06-16.md
docs/FINAL_HOLD_BLOCK_REVIEW_2026-06-16.md
docs/FINAL_WORKSPACE_STAGING_GROUPS_2026-06-16.md
docs/MACD_PLUGIN_ARCHITECTURE_DECISION_2026-06-16.md
docs/NEXT_STAGING_PLAN_AFTER_E407CB3_2026-06-16.md
docs/POST_CYCLE100_CLEANUP_CANDIDATES_2026-06-16.md
docs/POST_CYCLE100_MINIMAL_KEEP_SET_2026-06-16.md
docs/POST_CYCLE100_STAGING_PROPOSAL_2026-06-16.md
docs/POST_CYCLE100_WORKSPACE_REVIEW_RESULT_2026-06-16.md
docs/POST_E407CB3_REMAINING_WORKSPACE_REVIEW_2026-06-16.md
docs/README_FINAL_HUMAN_REVIEW_2026-06-16.md
```

This preview document itself is also a review-doc keep candidate if the human wants to preserve the cleanup plan.

## GENERATED_SAFETY_JUNK_DROP_CANDIDATE

Count: **1899**

Primary patterns:

```text
core/*ultimate*.py
core/*final*.py
core/*absolute*.py
core/*blocked*.py
core/*safety*.py
core/*lock*.py
core/*notification*.py
core/*validator*.py
core/*checker*.py
core/*enforcer*.py
core/*scorecard*.py
core/*gate*.py
core/*commit*.py
core/*git_add*.py
core/*operator*.py
core/*console*.py
core/*cycle*.py
tests/unit/test_*ultimate*.py
tests/unit/test_*final*.py
tests/unit/test_*absolute*.py
tests/unit/test_*blocked*.py
tests/unit/test_*safety*.py
tests/unit/test_*validator*.py
tests/unit/test_*checker*.py
scripts/run_*cycle*.py
docs/*cycle*.md
docs/*paper*.md
docs/*operator*.md
docs/*handoff*.md
```

Broad generated directories:

```text
core/
tests/
scripts/
docs/ generated reports except review keep candidates
```

Do not delete without a separate explicit cleanup authorization.

## LOCAL_HOLD

Count: **13**

```text
.mcp.json
execution_report.md
loop_status.md
task_from_chatgpt.md
relay/
research/
```

These are local app/config/run artifacts or local notes. Hold unless the human explicitly asks to delete or gitignore them.

## UNKNOWN_NEEDS_REVIEW

Count: **8**

```text
docs/AUTO_RUN_24H_WITH_BACKFILL_RUNBOOK.md
docs/api_contract_and_dependency_graph.md
docs/hold_block_file_register_2026-06-15.md
docs/octopusycc_mouse_trade_plan_2026-05-23_2026-05-30.md
docs/test_coverage_intent_matrix_2026-06-15.md
docs/test_quality_scorecard_2026-06-15.md
src/trade_plan_engine/alert_payload_builder.py
src/trade_plan_engine/macd_rebound_lifecycle.py
```

These are not recommended for deletion without a separate review pass.

## Cleanup Command Preview

Preview only. Do not execute without explicit human authorization.

Safer manual path: create a temporary manifest first, inspect it, then delete from the manifest.

```bash
# PREVIEW ONLY - write candidate manifest
git ls-files --others --exclude-standard \
  | grep -E '^(core/|tests/|scripts/)' \
  > /tmp/qq_drop_candidates.txt

git ls-files --others --exclude-standard docs \
  | grep -Ev 'docs/(FINAL_GIT_STATUS_REVIEW_2026-06-16.md|FINAL_HOLD_BLOCK_REVIEW_2026-06-16.md|FINAL_WORKSPACE_STAGING_GROUPS_2026-06-16.md|MACD_PLUGIN_ARCHITECTURE_DECISION_2026-06-16.md|NEXT_STAGING_PLAN_AFTER_E407CB3_2026-06-16.md|POST_CYCLE100_CLEANUP_CANDIDATES_2026-06-16.md|POST_CYCLE100_MINIMAL_KEEP_SET_2026-06-16.md|POST_CYCLE100_STAGING_PROPOSAL_2026-06-16.md|POST_CYCLE100_WORKSPACE_REVIEW_RESULT_2026-06-16.md|POST_E407CB3_REMAINING_WORKSPACE_REVIEW_2026-06-16.md|README_FINAL_HUMAN_REVIEW_2026-06-16.md|FINAL_UNTRACKED_CLEANUP_PREVIEW_AFTER_4FFABE2_2026-06-16.md)$' \
  >> /tmp/qq_drop_candidates.txt

# PREVIEW ONLY - inspect before any deletion
wc -l /tmp/qq_drop_candidates.txt
sed -n '1,120p' /tmp/qq_drop_candidates.txt
```

If the human later authorizes deletion, prefer a reviewed manifest-based cleanup over `git clean -fd`.

```bash
# DO NOT RUN WITHOUT AUTHORIZATION
# xargs rm -f < /tmp/qq_drop_candidates.txt
```

Hard hold for future cleanup:

```text
.mcp.json
relay/
research/
execution_report.md
loop_status.md
task_from_chatgpt.md
UNKNOWN_NEEDS_REVIEW paths
```
