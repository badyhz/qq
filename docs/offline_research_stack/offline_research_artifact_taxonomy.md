# Offline Research Artifact Taxonomy

## Artifact Types

| Type | Extension | Description |
|------|-----------|-------------|
| json | .json | Structured data, manifests, results |
| markdown | .md | Documentation, reports |
| html | .html | Rendered reports, UI |
| text | .txt | Plain text output |
| csv | .csv | Tabular data |
| log | .log | Execution logs |
| unknown | other | Unrecognized |

## Source Phases

| Phase | Directory Pattern |
|-------|------------------|
| workbench | multi_strategy_research_workbench |
| quality_gate | multi_strategy_research_quality_gate |
| artifact_browser | research_artifact_browser |
| comparison_analytics | research_comparison_analytics |
| human_review | research_human_review_packet |
| operator_bundle | offline_research_operator_bundle |
| experiment_library | offline_research_experiment_library_validation |
| governance | offline_research_governance_validation |
| frozen_inventory | frozen_inventory_review |
| decision_matrix | frozen_inventory_decision_matrix |
| archive_plan | frozen_inventory_archive_plan |

## Priority Assignment

| Condition | Priority |
|-----------|----------|
| frozen_inventory/decision_matrix/archive_plan phase | high |
| governance/quality_gate phase | high |
| Has safety_flags in manifest | high |
| human_review/operator_bundle phase | medium |
| All others | low |
