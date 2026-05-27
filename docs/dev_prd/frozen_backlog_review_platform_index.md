# Frozen Backlog Review Platform v1 — Documentation Index

## Overview

This index links all documentation, CLIs, core modules, and test files for the Frozen Backlog Review Platform.

The platform provides a comprehensive system for reviewing, validating, snapshotting, and reporting on 22 frozen backlog files that are held under `release_hold=HOLD`.

---

## Documentation

### Core Platform Docs

- [frozen_backlog_review_overview.md](frozen_backlog_review_overview.md) — Platform overview and architecture
- [frozen_backlog_review_report_cli.md](frozen_backlog_review_report_cli.md) — Report generation CLI usage
- [frozen_backlog_review_report_materializer.md](frozen_backlog_review_report_materializer.md) — Report materialization from inventory
- [frozen_backlog_report_validator.md](frozen_backlog_report_validator.md) — T1681: Report validation rules
- [frozen_backlog_report_snapshot.md](frozen_backlog_report_snapshot.md) — T1682: Snapshot system
- [frozen_backlog_report_diff.md](frozen_backlog_report_diff.md) — T1683: Diff engine for snapshot comparison
- [frozen_backlog_review_audit_cli.md](frozen_backlog_review_audit_cli.md) — T1684: Audit CLI usage

### Policy Docs

- [frozen_backlog_closeout.md](frozen_backlog_closeout.md) — Closeout procedures
- [frozen_backlog_commit_denial_policy.md](frozen_backlog_commit_denial_policy.md) — Commit denial rules
- [frozen_backlog_evidence_requirement.md](frozen_backlog_evidence_requirement.md) — Evidence requirements
- [frozen_backlog_high_risk_review_policy.md](frozen_backlog_high_risk_review_policy.md) — HIGH risk review rules
- [frozen_backlog_medium_risk_review_policy.md](frozen_backlog_medium_risk_review_policy.md) — MEDIUM risk review rules
- [frozen_backlog_human_approval_policy.md](frozen_backlog_human_approval_policy.md) — Human approval gates
- [frozen_backlog_inspection_only_policy.md](frozen_backlog_inspection_only_policy.md) — Inspection-only access
- [frozen_backlog_promotion_boundary.md](frozen_backlog_promotion_boundary.md) — Promotion boundaries
- [frozen_backlog_rollback_requirement.md](frozen_backlog_rollback_requirement.md) — Rollback requirements

### Acceptance / Safety / Closeout Packets

- [t1521_t1600_acceptance_packet.md](t1521_t1600_acceptance_packet.md)
- [t1521_t1600_safety_boundary_packet.md](t1521_t1600_safety_boundary_packet.md)
- [t1521_t1600_final_closeout_report.md](t1521_t1600_final_closeout_report.md)
- [t1601_t1800_acceptance_packet.md](t1601_t1800_acceptance_packet.md)
- [t1601_t1800_safety_boundary_packet.md](t1601_t1800_safety_boundary_packet.md)
- [t1601_t1800_final_closeout_report.md](t1601_t1800_final_closeout_report.md)
- [t1061_t1160_final_closeout_report.md](t1061_t1160_final_closeout_report.md)
- [t1061_t1160_safety_boundary_packet.md](t1061_t1160_safety_boundary_packet.md)
- [t1161_t1260_final_closeout_report.md](t1161_t1260_final_closeout_report.md)
- [t1161_t1260_safety_boundary_packet.md](t1161_t1260_safety_boundary_packet.md)
- [t1261_t1360_final_closeout_report.md](t1261_t1360_final_closeout_report.md)
- [t1261_t1360_safety_boundary_packet.md](t1261_t1360_safety_boundary_packet.md)
- [t1361_t1440_final_closeout_report.md](t1361_t1440_final_closeout_report.md)
- [t1441_t1520_final_closeout_report.md](t1441_t1520_final_closeout_report.md)

---

## CLIs

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/generate_frozen_backlog_review_report.py` | Generate report (MD + JSON) | `--output-dir DIR [--mode full\|summary]` |
| `scripts/validate_frozen_backlog_review_report.py` | Validate a report JSON file | `--input PATH` |
| `scripts/snapshot_frozen_backlog_review_report.py` | Create a snapshot of report | `--input PATH --output PATH` |
| `scripts/diff_frozen_backlog_review_reports.py` | Diff two report/snapshot JSON files | `--before PATH --after PATH --output-dir DIR` |
| `scripts/render_frozen_backlog_review_dashboard.py` | Render HTML dashboard | `--output-dir DIR` |
| `scripts/build_frozen_backlog_review_bundle.py` | Build full board packet bundle | `--output-dir DIR` |
| `scripts/run_frozen_backlog_review_audit.py` | Audit orchestrator | `--output-dir DIR [--mode full\|summary] [--snapshot PATH]` |
| `scripts/run_frozen_backlog_platform_audit.py` | Platform audit (end-to-end) | `--output-dir DIR [--mode full\|summary] [--snapshot PATH]` |
| `scripts/generate_frozen_backlog_agent_handoff.py` | Generate agent handoff prompt | `--output-md PATH` |
| `scripts/export_frozen_backlog_review_schema.py` | Export schema | `--output PATH` |

---

## Core Modules

### Data Model

| Module | Purpose |
|--------|---------|
| `core/frozen_backlog_inventory_record.py` | FrozenBacklogInventoryRecord dataclass |
| `core/frozen_backlog_inventory.py` | FROZEN_BACKLOG_INVENTORY constant (22 records) |
| `core/frozen_backlog_report_record.py` | FrozenBacklogReportRecord dataclass |
| `core/frozen_backlog_report_summary.py` | FrozenBacklogReportSummary dataclass |
| `core/frozen_backlog_snapshot.py` | FrozenBacklogSnapshot dataclass |
| `core/frozen_backlog_validation_result.py` | FrozenBacklogValidationResult dataclass |
| `core/frozen_backlog_artifact_entry.py` | ArtifactEntry dataclass |
| `core/frozen_backlog_manifest.py` | FrozenBacklogManifest dataclass |

### Rendering

| Module | Purpose |
|--------|---------|
| `core/frozen_backlog_report_renderer.py` | Markdown report rendering |
| `core/frozen_backlog_report_json.py` | JSON report rendering |
| `core/frozen_backlog_dashboard_renderer.py` | HTML dashboard rendering |
| `core/frozen_backlog_board_packet_renderer.py` | Board packet markdown rendering |
| `core/frozen_backlog_manifest_renderer.py` | Manifest rendering |

### Processing

| Module | Purpose |
|--------|---------|
| `core/frozen_backlog_report_materializer.py` | Materialize report from inventory |
| `core/frozen_backlog_report_validator.py` | Validate report data |
| `core/frozen_backlog_snapshot_manager.py` | Snapshot create/read/write |
| `core/frozen_backlog_manifest_builder.py` | Build manifest from artifact files |
| `core/frozen_backlog_agent_handoff_generator.py` | Generate agent handoff prompt |

### Extended Models

| Module | Purpose |
|--------|---------|
| `core/frozen_backlog_decision_matrix.py` | Decision matrix |
| `core/frozen_backlog_decision_item.py` | Decision item |
| `core/frozen_backlog_decision_renderer.py` | Decision rendering |
| `core/frozen_backlog_diff_engine.py` | Diff engine |
| `core/frozen_backlog_diff_renderer.py` | Diff rendering |
| `core/frozen_backlog_verdict_engine.py` | Verdict engine |
| `core/frozen_backlog_review.py` | Review model |
| `core/frozen_backlog_review_renderer.py` | Review rendering |

---

## Test Files

| Test File | Coverage |
|-----------|----------|
| `tests/unit/test_frozen_backlog_inventory.py` | Inventory data model |
| `tests/unit/test_frozen_backlog_report_materializer.py` | Report materialization |
| `tests/unit/test_frozen_backlog_report_renderer.py` | Markdown rendering |
| `tests/unit/test_frozen_backlog_report_json.py` | JSON rendering |
| `tests/unit/test_frozen_backlog_report_validator.py` | Report validation |
| `tests/unit/test_frozen_backlog_snapshot.py` | Snapshot system |
| `tests/unit/test_frozen_backlog_dashboard_renderer.py` | HTML dashboard |
| `tests/unit/test_frozen_backlog_bundle_builder.py` | Bundle builder CLI |
| `tests/unit/test_frozen_backlog_manifest.py` | Manifest system |
| `tests/unit/test_frozen_backlog_diff.py` | Diff engine |
| `tests/unit/test_frozen_backlog_decision_matrix.py` | Decision matrix |
| `tests/unit/test_frozen_backlog_verdict_engine.py` | Verdict engine |
| `tests/unit/test_frozen_backlog_review.py` | Review model |
| `tests/unit/test_frozen_backlog_schema_exporter.py` | Schema export |
| `tests/unit/test_frozen_backlog_golden_fixtures.py` | Golden fixtures |
| `tests/unit/test_frozen_backlog_golden_regression.py` | Golden regression |
| `tests/unit/test_frozen_backlog_mutation.py` | Mutation tests |
| `tests/unit/test_frozen_backlog_report_safety.py` | Safety invariants |
| `tests/unit/test_frozen_backlog_status_compatibility.py` | Status compat |
| `tests/unit/test_frozen_backlog_decision_compatibility.py` | Decision compat |
| `tests/unit/test_frozen_backlog_platform_audit.py` | Platform audit runner |
| `tests/unit/test_frozen_backlog_agent_handoff.py` | Agent handoff generator |

---

## Safety Invariants

- `release_hold` must always be `HOLD`
- `no_live`, `no_submit`, `no_exchange`, `no_runtime_integration`, `no_planner_integration` must all be `True`
- 22 frozen files, 9 HIGH risk, 13 MEDIUM risk
- No network calls, no exchange calls, no order placement
- Explicit `git add` only — never `git add .`
