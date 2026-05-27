# Runtime Governance Artifact Index

Static expected index of all governance artifacts T794-T818.

## Overview

25 tasks x 3 artifacts each = 75 artifacts.

Each task produces:
- **core** — `core/runtime_governance_<name>.py`
- **test** — `tests/unit/test_runtime_governance_<name>.py`
- **doc** — `docs/runtime_governance_<name>.md` (or umbrella doc)

## Tasks

| Task ID | Module | Purpose |
|---------|--------|---------|
| T794 | runtime_governance_contract | Core contract dataclass and serialization |
| T795 | runtime_governance_dry_run_adapter | Dry-run-only execution adapter |
| T796 | runtime_governance_audit_event | Audit event dataclass |
| T797 | runtime_governance_preflight_packet | Preflight readiness packet |
| T798 | runtime_governance_scenario_catalog | Governance test scenarios |
| T799 | runtime_governance_preflight_renderer | Preflight renderer to markdown |
| T800 | runtime_governance_schema_checker | Schema validation |
| T801 | runtime_governance_reason_codes | Enumerated reason codes |
| T802 | runtime_governance_policy_matrix | Policy-to-action mapping |
| T803 | runtime_governance_invariant_checker | State consistency checks |
| T804 | runtime_governance_sample_factory | Test/sample data factory |
| T805 | runtime_governance_stack_manifest | Expected modules manifest |
| T806 | runtime_governance_blocker_summary | Blocker summary |
| T807 | runtime_governance_no_submit_evidence_packet | No-submit evidence |
| T808 | runtime_governance_regression_packet | Regression analysis packet |
| T809 | runtime_governance_phase_control_report | Phase transition tracking |
| T810 | runtime_governance_dry_run_matrix_report | Dry-run coverage matrix |
| T811 | runtime_governance_readiness_score | Progression readiness score |
| T812 | runtime_governance_transition_checklist | Transition gate checklist |
| T813 | runtime_governance_closeout_checklist | Stage closeout checklist |
| T814 | runtime_governance_scenario_batch_evaluator | Batch scenario evaluator |
| T815 | runtime_governance_frozen_boundary_map | Frozen boundary mapping |
| T816 | runtime_governance_approval_gate_spec | Approval gate specification |
| T817 | runtime_governance_artifact_index | This artifact index |
| T818 | runtime_governance_future_task_planner | Future task scheduling |

## API

```python
from core.runtime_governance_artifact_index import (
    build_runtime_governance_artifact_index,
    artifact_index_to_dict,
    artifact_index_to_markdown,
    summarize_artifact_index,
)

artifacts = build_runtime_governance_artifact_index()  # 75 items
as_dicts = artifact_index_to_dict(artifacts)
md = artifact_index_to_markdown(artifacts)
summary = summarize_artifact_index(artifacts)
```

## Constraints

- Pure data. No I/O. No network. No repo scanning.
- Frozen dataclass. Deterministic output.
- Static expected index — does not verify files exist on disk.
