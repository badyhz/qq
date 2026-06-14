"""De facto spec registry: documents that implementation serves as the specification."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class SpecEntry:
    entry_id: str
    stage_id: str
    implementation_artifact: str
    runtime_report: str
    suite_runner: str
    test_files: tuple[str, ...]
    status: str
    spec_source_type: str
    def to_dict(self) -> dict:
        return {"entry_id": self.entry_id, "stage_id": self.stage_id,
                "implementation_artifact": self.implementation_artifact,
                "runtime_report": self.runtime_report,
                "suite_runner": self.suite_runner,
                "test_files": list(self.test_files),
                "status": self.status, "spec_source_type": self.spec_source_type}


@dataclass(frozen=True)
class DeFactoSpecRegistry:
    registry_id: str
    created_at: str
    entries: tuple[SpecEntry, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"registry_id": self.registry_id, "created_at": self.created_at,
                "entries": [e.to_dict() for e in self.entries],
                "final_verdict": self.final_verdict}


ENTRIES = (
    SpecEntry("DSR_001", "STG_RO_001",
        "src/runtime_integrations/testnet_readonly_discovery/",
        "reports/testnet_readonly_discovery/",
        "run_testnet_readonly_discovery_suite.py",
        ("test_readonly_discovery_design.py", "test_credential_policy_stub.py",
         "test_exchange_capability_inventory.py", "test_readonly_adapter_contract.py",
         "test_discovery_governance_checklist.py", "test_readonly_discovery_dry_run_packet.py",
         "test_readonly_discovery_safety_regression.py", "test_testnet_readonly_discovery_suite.py"),
        "COMPLETE", "IMPLEMENTATION_AS_DE_FACTO_SPEC"),
    SpecEntry("DSR_002", "STG_RO_002",
        "src/runtime_integrations/testnet_readonly_preapproval/",
        "reports/testnet_readonly_preapproval/",
        "run_testnet_readonly_preapproval_suite.py",
        ("test_readonly_discovery_approval_packet.py", "test_no_network_preflight_evidence.py",
         "test_credential_handling_sop.py", "test_readonly_discovery_operator_checklist.py",
         "test_readonly_discovery_manual_review_queue.py", "test_readonly_preapproval_safety_regression.py",
         "test_testnet_readonly_preapproval_suite.py"),
        "COMPLETE", "IMPLEMENTATION_AS_DE_FACTO_SPEC"),
    SpecEntry("DSR_003", "STG_RO_003",
        "src/runtime_integrations/testnet_readonly_release_gate/",
        "reports/testnet_readonly_release_gate/",
        "run_testnet_readonly_release_gate_suite.py",
        ("test_readonly_discovery_release_gate.py", "test_readonly_release_blocker_ledger.py",
         "test_readonly_operator_signoff_draft.py", "test_readonly_release_gate_safety_regression.py",
         "test_testnet_readonly_release_gate_suite.py"),
        "COMPLETE", "IMPLEMENTATION_AS_DE_FACTO_SPEC"),
    SpecEntry("DSR_004", "STG_RO_004",
        "src/runtime_integrations/testnet_readonly_final_approval_simulator/",
        "reports/testnet_readonly_final_approval_simulator/",
        "run_testnet_readonly_final_approval_simulator_suite.py",
        ("test_readonly_final_approval_simulator.py", "test_network_on_blocker_drill.py",
         "test_readonly_human_signoff_archive.py", "test_testnet_readonly_final_approval_simulator_suite.py"),
        "COMPLETE", "IMPLEMENTATION_AS_DE_FACTO_SPEC"),
    SpecEntry("DSR_005", "STG_RO_005",
        "src/runtime_integrations/testnet_readonly_dry_execution_rehearsal/",
        "reports/testnet_readonly_dry_execution_rehearsal/",
        "run_testnet_readonly_dry_execution_rehearsal_suite.py",
        ("test_readonly_dry_execution_rehearsal.py", "test_readonly_endpoint_allowlist_stub.py",
         "test_readonly_audit_redaction_pack.py", "test_readonly_dry_execution_artifact_manifest.py",
         "test_testnet_readonly_dry_execution_rehearsal_suite.py"),
        "COMPLETE", "IMPLEMENTATION_AS_DE_FACTO_SPEC"),
    SpecEntry("DSR_006", "STG_RO_006",
        "src/runtime_integrations/testnet_readonly_final_governance_freeze/",
        "reports/testnet_readonly_final_governance_freeze/",
        "run_testnet_readonly_final_governance_freeze_suite.py",
        ("test_readonly_final_governance_freeze.py", "test_readonly_operator_handoff_packet.py",
         "test_readonly_no_submit_release_archive.py", "test_readonly_freeze_integrity_manifest.py",
         "test_testnet_readonly_final_governance_freeze_suite.py"),
        "COMPLETE", "IMPLEMENTATION_AS_DE_FACTO_SPEC"),
)


def create_registry() -> DeFactoSpecRegistry:
    return DeFactoSpecRegistry(
        registry_id=f"DFR_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        entries=ENTRIES,
        final_verdict="DE_FACTO_SPEC_REGISTRY_READY|ALL_IMPLEMENTATIONS_DOCUMENTED|EXTERNAL_PRD_NOT_FOUND|IMPLEMENTATION_AS_DE_FACTO_SPEC",
    )


def write_registry(registry: DeFactoSpecRegistry, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(registry.to_dict(), indent=2), encoding="utf-8")


def render_report(registry: DeFactoSpecRegistry) -> str:
    lines = ["# De Facto Spec Registry", "",
        f"**registry_id={registry.registry_id}**",
        f"**entries={len(registry.entries)}**",
        f"**verdict={registry.final_verdict}**", "",
        "## Entries", "",
        "| ID | Stage | Artifact | Tests | Status | Source Type |",
        "|----|-------|----------|-------|--------|-------------|"]
    for e in registry.entries:
        lines.append(f"| {e.entry_id} | {e.stage_id} | {e.implementation_artifact} | {len(e.test_files)} | {e.status} | {e.spec_source_type} |")
    lines.extend(["", "## Conclusion", "",
        "DE_FACTO_SPEC_REGISTRY_READY",
        "ALL_IMPLEMENTATIONS_DOCUMENTED",
        "EXTERNAL_PRD_NOT_FOUND",
        "IMPLEMENTATION_AS_DE_FACTO_SPEC", ""])
    return "\n".join(lines)
