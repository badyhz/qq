# Offline Research Result Catalog

## Purpose

Build an offline catalog for generated research outputs, reports, bundles, manifests, and review packets.

## Scanned Directories

- /tmp/multi_strategy_research_workbench
- /tmp/multi_strategy_research_quality_gate
- /tmp/research_artifact_browser
- /tmp/research_comparison_analytics
- /tmp/research_human_review_packet
- /tmp/offline_research_operator_bundle
- /tmp/offline_research_experiment_library_validation
- /tmp/offline_research_governance_validation
- /tmp/frozen_inventory_review
- /tmp/frozen_inventory_decision_matrix
- /tmp/frozen_inventory_archive_plan

## Artifact Fields

- path — full path to artifact
- artifact_type — json, markdown, html, text, csv, log, unknown
- size_bytes — file size
- sha256 — content hash
- json_valid — whether JSON parses correctly
- has_markdown — whether markdown exists in same dir
- has_html — whether HTML exists in same dir
- source_phase — which phase produced this artifact
- safety_flags — extracted from manifest if present
- release_hold — from manifest or default
- advisory_only — from manifest or default
- retention_class — KEEP_LATEST, KEEP_TAGGED, KEEP_FOR_AUDIT, TEMP_REGENERABLE, REVIEW_REQUIRED, UNKNOWN
- review_priority — high, medium, low

## Retention Classes

| Class | Meaning |
|-------|---------|
| KEEP_LATEST | Keep most recent version |
| KEEP_TAGGED | Keep tagged versions |
| KEEP_FOR_AUDIT | Keep for audit trail |
| TEMP_REGENERABLE | Can be regenerated |
| REVIEW_REQUIRED | Needs human review |
| UNKNOWN | Cannot determine |

## Safety Boundary

- No network imports
- No scanning repo frozen files
- release_hold = HOLD
- Advisory only. Human review required.

## CLI

```bash
python3 scripts/build_offline_research_result_catalog.py \
    --output-dir /tmp/offline_research_result_catalog \
    --strict \
    --release-hold HOLD
```
