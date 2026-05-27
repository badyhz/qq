# Runtime Governance Stack Manifest

## Overview

Pure-data manifest for the runtime governance modules T794-T805.
No repo scanning. No file I/O. No network. Deterministic output.

## API

### `build_expected_runtime_governance_stack_manifest(overrides=None) -> RuntimeGovernanceStackManifest`

Build manifest with expected components. `overrides` maps `task_id -> status` ("PASS", "WARN", "FAIL").
Defaults to "PASS" for all.

### `runtime_manifest_to_dict(manifest) -> Dict`

Serialize manifest to plain dict. Deterministic.

### `runtime_manifest_to_markdown(manifest) -> str`

Render manifest as markdown table. Deterministic, no timestamps.

### `summarize_runtime_manifest(manifest) -> Dict[str, Any]`

Summarize counts by status. Deterministic.

## Component List

| Task | Name | Module | Status |
|------|------|--------|--------|
| T794 | runtime_governance_contract | core/runtime_governance_contract.py | PASS |
| T795 | runtime_governance_dry_run_adapter | core/runtime_governance_dry_run_adapter.py | PASS |
| T796 | runtime_governance_audit_event | core/runtime_governance_audit_event.py | PASS |
| T797 | runtime_governance_preflight_packet | core/runtime_governance_preflight_packet.py | PASS |
| T798 | runtime_governance_scenario_catalog | core/runtime_governance_scenario_catalog.py | PASS |
| T799 | runtime_governance_preflight_renderer | core/runtime_governance_preflight_renderer.py | PASS |
| T800 | runtime_governance_schema_checker | core/runtime_governance_schema_checker.py | PASS |
| T801 | runtime_governance_reason_codes | core/runtime_governance_reason_codes.py | PASS |
| T802 | runtime_governance_policy_matrix | core/runtime_governance_policy_matrix.py | PASS |
| T803 | runtime_governance_invariant_checker | core/runtime_governance_invariant_checker.py | PASS |
| T804 | runtime_governance_sample_factory | core/runtime_governance_sample_factory.py | PASS |
| T805 | runtime_governance_stack_manifest | core/runtime_governance_stack_manifest.py | PASS |

## Verdict Logic

- PASS: all components PASS
- WARN: any component WARN
- FAIL: any component FAIL

## Determinism

All functions return identical output for identical input. No timestamps, no randomness, no I/O.
