"""Readonly stage inventory."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class StageEntry:
    stage_id: str
    stage_name: str
    milestone: str
    commit: str
    tag: str
    package_path: str
    runner_files: tuple[str, ...]
    test_files: tuple[str, ...]
    suite_runner: str
    status: str
    notes: str
    def to_dict(self) -> dict:
        return {
            "stage_id": self.stage_id, "stage_name": self.stage_name,
            "milestone": self.milestone, "commit": self.commit, "tag": self.tag,
            "package_path": self.package_path,
            "runner_files": list(self.runner_files),
            "test_files": list(self.test_files),
            "suite_runner": self.suite_runner,
            "status": self.status, "notes": self.notes,
        }


@dataclass(frozen=True)
class StageInventory:
    inventory_id: str
    created_at: str
    stages: tuple[StageEntry, ...]
    def to_dict(self) -> dict:
        return {"inventory_id": self.inventory_id, "created_at": self.created_at,
                "stages": [s.to_dict() for s in self.stages]}


STAGES = (
    StageEntry(
        "STG_RO_001", "read-only discovery design", "T230001-T245000",
        "909ed61", "testnet-readonly-discovery-design-complete",
        "src/runtime_integrations/testnet_readonly_discovery",
        ("run_readonly_discovery_design.py", "run_credential_policy_stub.py",
         "run_exchange_capability_inventory.py", "run_readonly_adapter_contract.py",
         "run_discovery_governance_checklist.py", "run_readonly_discovery_dry_run_packet.py",
         "run_readonly_discovery_safety_regression.py"),
        ("test_readonly_discovery_design.py", "test_credential_policy_stub.py",
         "test_exchange_capability_inventory.py", "test_readonly_adapter_contract.py",
         "test_discovery_governance_checklist.py", "test_readonly_discovery_dry_run_packet.py",
         "test_readonly_discovery_safety_regression.py", "test_testnet_readonly_discovery_suite.py"),
        "run_testnet_readonly_discovery_suite.py", "COMPLETE",
        "7 modules, 7 steps, chains mock_closeout_suite",
    ),
    StageEntry(
        "STG_RO_002", "read-only preapproval", "T245001-T260000",
        "2a4d4c1", "testnet-readonly-preapproval-complete",
        "src/runtime_integrations/testnet_readonly_preapproval",
        ("run_readonly_discovery_approval_packet.py", "run_no_network_preflight_evidence.py",
         "run_credential_handling_sop.py", "run_readonly_discovery_operator_checklist.py",
         "run_readonly_discovery_manual_review_queue.py", "run_readonly_preapproval_safety_regression.py"),
        ("test_readonly_discovery_approval_packet.py", "test_no_network_preflight_evidence.py",
         "test_credential_handling_sop.py", "test_readonly_discovery_operator_checklist.py",
         "test_readonly_discovery_manual_review_queue.py", "test_readonly_preapproval_safety_regression.py",
         "test_testnet_readonly_preapproval_suite.py"),
        "run_testnet_readonly_preapproval_suite.py", "COMPLETE",
        "6 modules, 6 steps, chains discovery_suite",
    ),
    StageEntry(
        "STG_RO_003", "read-only release gate", "T260001-T275000",
        "3ec4501", "testnet-readonly-release-gate-complete",
        "src/runtime_integrations/testnet_readonly_release_gate",
        ("run_readonly_discovery_release_gate.py", "run_network_off_execution_packet.py",
         "run_credential_air_gap_policy.py", "run_readonly_release_blocker_ledger.py",
         "run_readonly_operator_signoff_draft.py", "run_readonly_release_gate_safety_regression.py"),
        ("test_readonly_discovery_release_gate.py", "test_readonly_release_blocker_ledger.py",
         "test_readonly_operator_signoff_draft.py", "test_readonly_release_gate_safety_regression.py",
         "test_testnet_readonly_release_gate_suite.py"),
        "run_testnet_readonly_release_gate_suite.py", "COMPLETE",
        "5 modules, 6 steps, chains discovery+preapproval",
    ),
    StageEntry(
        "STG_RO_004", "final approval simulator", "T275001-T290000",
        "fb778db", "testnet-readonly-final-approval-simulator-complete",
        "src/runtime_integrations/testnet_readonly_final_approval_simulator",
        ("run_readonly_final_approval_simulator.py", "run_network_on_blocker_drill.py",
         "run_readonly_human_signoff_archive.py", "run_final_approval_safety_regression.py"),
        ("test_readonly_final_approval_simulator.py", "test_readonly_human_signoff_archive.py",
         "test_testnet_readonly_final_approval_simulator_suite.py"),
        "run_testnet_readonly_final_approval_simulator_suite.py", "COMPLETE",
        "3 modules, 4 steps, chains discovery+preapproval+release_gate",
    ),
    StageEntry(
        "STG_RO_005", "dry execution rehearsal", "T290001-T305000",
        "2e9a676", "testnet-readonly-dry-execution-rehearsal-complete",
        "src/runtime_integrations/testnet_readonly_dry_execution_rehearsal",
        ("run_readonly_dry_execution_rehearsal.py", "run_endpoint_allowlist_stub.py",
         "run_audit_redaction_pack.py", "run_dry_execution_safety_regression.py"),
        ("test_readonly_dry_execution_rehearsal.py", "test_testnet_readonly_dry_execution_rehearsal_suite.py"),
        "run_testnet_readonly_dry_execution_rehearsal_suite.py", "COMPLETE",
        "3 modules, 4 steps, chains 4 prior suites",
    ),
    StageEntry(
        "STG_RO_006", "final governance freeze", "T305001-T320000",
        "0f12810", "testnet-readonly-final-governance-freeze-complete",
        "src/runtime_integrations/testnet_readonly_final_governance_freeze",
        ("run_readonly_final_governance_freeze.py", "run_operator_handoff_packet.py",
         "run_no_submit_release_archive.py", "run_final_governance_safety_regression.py"),
        ("test_readonly_final_governance_freeze.py", "test_testnet_readonly_final_governance_freeze_suite.py"),
        "run_testnet_readonly_final_governance_freeze_suite.py", "COMPLETE",
        "3 modules, 4 steps, chains 5 prior suites",
    ),
)


def create_inventory() -> StageInventory:
    return StageInventory(
        inventory_id=f"SI_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        stages=STAGES,
    )


def write_inventory(inventory: StageInventory, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(inventory.to_dict(), indent=2), encoding="utf-8")


def render_report(inventory: StageInventory) -> str:
    lines = ["# Readonly Stage Inventory", "",
        f"**inventory_id={inventory.inventory_id}**",
        f"**total_stages={len(inventory.stages)}**", "",
        "## Stages", "",
        "| ID | Milestone | Commit | Tag | Modules | Status |",
        "|----|-----------|--------|-----|---------|--------|"]
    for s in inventory.stages:
        lines.append(f"| {s.stage_id} | {s.milestone} | {s.commit} | {s.tag} | {len(s.runner_files)} | {s.status} |")
    lines.extend(["", "## Conclusion", "", "READONLY_STAGE_INVENTORY_READY", ""])
    return "\n".join(lines)
