"""Review navigation report."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class NavigationEntry:
    entry_id: str
    section: str
    title: str
    description: str
    artifact_refs: tuple[str, ...]
    def to_dict(self) -> dict:
        return {"entry_id": self.entry_id, "section": self.section, "title": self.title, "description": self.description, "artifact_refs": list(self.artifact_refs)}


@dataclass(frozen=True)
class NavigationReport:
    report_id: str
    created_at: str
    entries: tuple[NavigationEntry, ...]
    def to_dict(self) -> dict:
        return {"report_id": self.report_id, "created_at": self.created_at, "entries": [e.to_dict() for e in self.entries]}


NAVIGATION_ENTRIES = (
    NavigationEntry("NAV_001", "overview", "Milestone Summary", "T185001-T200000 mock replay harness and T200001-T215000 mock review artifacts", ("mock_replay_suite_manifest.json",)),
    NavigationEntry("NAV_002", "evidence", "Evidence Bundle", "Complete mock field-test evidence bundle with 10 items", ("evidence_bundle.json", "evidence_browser_result.json")),
    NavigationEntry("NAV_003", "approval", "Approval Packets", "Human approval packet v3 and comparator", ("human_approval_packet_v3.json", "approval_packet_comparison.json")),
    NavigationEntry("NAV_004", "replay", "Replay Traces", "All 13 scenario replay traces with governance validation", ("replay_traces.json", "replay_scenario_matrix.json")),
    NavigationEntry("NAV_005", "governance", "Governance Checks", "Trace validator and governance blocker verification", ("trace_validator_checks.json",)),
    NavigationEntry("NAV_006", "transport", "Mock Transport", "Mock transport contract, vault stub, adapter skeleton", ("mock_transport_contract.json", "vault_stub_state.json")),
    NavigationEntry("NAV_007", "spec", "Adapter Spec", "External testnet adapter specification and architecture", ("external_adapter_spec.md", "credential_vault_architecture.md")),
    NavigationEntry("NAV_008", "safety", "Safety Regression", "No-submit safety regression scan results", ("replay_safety_regression.json", "mock_review_safety_regression.json")),
    NavigationEntry("NAV_009", "review", "Operator Review Index", "Index of all review artifacts with search and filter", ("operator_review_index.json",)),
    NavigationEntry("NAV_010", "handoff", "Final Handoff", "Final suite handoff document with all conclusions", ("final_external_testnet_mock_review_handoff.md",)),
)


def create_report() -> NavigationReport:
    return NavigationReport(
        report_id=f"NAV_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        entries=NAVIGATION_ENTRIES,
    )


def search_entries(report: NavigationReport, query: str) -> list[NavigationEntry]:
    q = query.lower()
    return [e for e in report.entries if q in e.title.lower() or q in e.section.lower() or q in e.description.lower()]


def write_report(report: NavigationReport, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def render_report(report: NavigationReport) -> str:
    lines = ["# Review Navigation Report", "",
        f"**report_id={report.report_id}**",
        "**MOCK_REVIEW_NAVIGATION_ONLY**",
        "**REAL_TESTNET_SUBMIT_NOT_ALLOWED**", "",
        f"Total entries: {len(report.entries)}", "",
        "## Navigation", ""]
    for e in report.entries:
        lines.extend([f"### {e.title}", "",
            f"**Section:** {e.section}",
            f"**Description:** {e.description}",
            f"**Artifacts:** {', '.join(e.artifact_refs)}", ""])
    lines.extend(["## Conclusion", "", "REVIEW_NAVIGATION_REPORT_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
