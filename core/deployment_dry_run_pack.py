"""T42001 — Deployment Dry-run Pack.

Pure deterministic. No I/O. No network.
Simulates local deployment steps without performing real operations.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED_DPK = "HOLD"

REQUIRED_CORE_MODULES = (
    "core/alert_center.py",
    "core/alert_source_adapter_registry.py",
    "core/dangerous_runtime_isolator.py",
    "core/deployment_dry_run_pack.py",
    "core/final_handoff_pack.py",
    "core/frozen_cleanup_decision_matrix.py",
    "core/frozen_cleanup_dry_run_executor.py",
    "core/frozen_cleanup_evidence_recorder.py",
    "core/frozen_cleanup_final_inventory.py",
    "core/frozen_cleanup_handoff_pack.py",
    "core/frozen_cleanup_report.py",
    "core/operator_console.py",
    "core/operator_dashboard_renderer.py",
    "core/promotion_approval_packet.py",
    "core/promotion_decision_engine.py",
    "core/promotion_evidence_loader.py",
    "core/promotion_rollback_plan.py",
    "core/research_artifact_registry.py",
    "core/safe_archive_planner.py",
    "core/shadow_pipeline_registry.py",
    "core/strategy_promotion_board.py",
    "core/strategy_registry.py",
    "core/testnet_dry_run_adapter_registry.py",
    "core/testnet_dry_run_orchestrator.py",
    "core/untracked_runtime_inventory.py",
)

REQUIRED_RUNNER_SCRIPTS = (
    "scripts/run_alert_center_dry_run.py",
    "scripts/run_alert_source_adapter_registry.py",
    "scripts/run_dangerous_runtime_isolation.py",
    "scripts/run_frozen_cleanup_governance.py",
    "scripts/run_operator_dashboard.py",
    "scripts/run_phase5_final.py",
    "scripts/run_promotion_gate.py",
    "scripts/run_research_artifact_registry.py",
    "scripts/run_shadow_pipeline_registry.py",
    "scripts/run_strategy_registry.py",
    "scripts/run_testnet_dry_run_adapter_registry.py",
    "scripts/run_untracked_runtime_inventory.py",
)


@dataclass(frozen=True)
class DeploymentStep:
    """Single deployment step in dry-run."""
    step_id: str
    step_name: str
    description: str
    would_execute: bool
    would_modify_files: bool
    would_install_deps: bool
    would_start_services: bool
    simulation_only: bool
    human_approval_required: bool
    advisory_only: bool

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "description": self.description,
            "would_execute": self.would_execute,
            "would_modify_files": self.would_modify_files,
            "would_install_deps": self.would_install_deps,
            "would_start_services": self.would_start_services,
            "simulation_only": self.simulation_only,
            "human_approval_required": self.human_approval_required,
            "advisory_only": self.advisory_only,
        }


DEPLOYMENT_STEPS = [
    {
        "name": "verify_core_modules",
        "desc": "Verify all required core modules are present",
    },
    {
        "name": "verify_runner_scripts",
        "desc": "Verify all runner scripts are present",
    },
    {
        "name": "verify_test_suite",
        "desc": "Verify test suite passes (dry-run: check only)",
    },
    {
        "name": "verify_no_real_submit",
        "desc": "Verify no real submit permissions are enabled",
    },
    {
        "name": "verify_dry_run_mode",
        "desc": "Verify system is in dry-run mode",
    },
    {
        "name": "generate_deployment_manifest",
        "desc": "Generate deployment manifest with hashes",
    },
    {
        "name": "generate_deployment_checklist",
        "desc": "Generate human-readable deployment checklist",
    },
]


def build_deployment_steps() -> list[DeploymentStep]:
    """Build deployment steps for dry-run simulation."""
    steps = []
    for i, s in enumerate(DEPLOYMENT_STEPS):
        steps.append(DeploymentStep(
            step_id=f"deploy_step_{i:03d}",
            step_name=s["name"],
            description=s["desc"],
            would_execute=False,
            would_modify_files=False,
            would_install_deps=False,
            would_start_services=False,
            simulation_only=True,
            human_approval_required=True,
            advisory_only=True,
        ))
    return steps


def compute_pack_hash(steps: list[DeploymentStep]) -> str:
    raw = json.dumps([s.to_dict() for s in steps], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_deployment_checklist_markdown(steps: list[DeploymentStep]) -> str:
    lines = [
        "# Deployment Dry-run Checklist",
        "",
        f"**Total steps:** {len(steps)}",
        "",
        "## Checklist",
        "",
    ]
    for s in steps:
        lines.append(f"- [ ] **{s.step_name}**: {s.description}")
        lines.append(f"  - Simulation only: {s.simulation_only}")
        lines.append(f"  - Human approval required: {s.human_approval_required}")

    lines.append("")
    lines.append("## Required Core Modules")
    lines.append("")
    for m in REQUIRED_CORE_MODULES:
        lines.append(f"- `{m}`")

    lines.append("")
    lines.append("## Required Runner Scripts")
    lines.append("")
    for s in REQUIRED_RUNNER_SCRIPTS:
        lines.append(f"- `{s}`")

    lines.append("")
    return "\n".join(lines)


def render_deployment_manifest_markdown(steps: list[DeploymentStep]) -> str:
    lines = [
        "# Deployment Manifest",
        "",
        "| Step | Name | Sim Only | Advisory | Human Approval |",
        "|------|------|----------|----------|----------------|",
    ]
    for s in steps:
        lines.append(
            f"| {s.step_id} | {s.step_name} | {s.simulation_only} "
            f"| {s.advisory_only} | {s.human_approval_required} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_json(steps: list[DeploymentStep], out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([s.to_dict() for s in steps], indent=2), encoding="utf-8")


def write_manifest(steps: list[DeploymentStep], out_path, release_hold: str) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "total_steps": len(steps),
        "release_hold": release_hold,
        "pack_hash": compute_pack_hash(steps),
        "all_simulation_only": all(s.simulation_only for s in steps),
        "all_advisory_only": all(s.advisory_only for s in steps),
        "all_human_approval_required": all(s.human_approval_required for s in steps),
        "required_core_modules_count": len(REQUIRED_CORE_MODULES),
        "required_runner_scripts_count": len(REQUIRED_RUNNER_SCRIPTS),
    }
    p.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(content: str, out_path) -> None:
    import pathlib
    p = pathlib.Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
