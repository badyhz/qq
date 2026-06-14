"""Mock review closeout summary."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class StageRecord:
    stage_id: str
    milestone: str
    title: str
    commit: str
    tag: str
    capabilities: tuple[str, ...]
    status: str
    def to_dict(self) -> dict:
        return {"stage_id": self.stage_id, "milestone": self.milestone, "title": self.title, "commit": self.commit, "tag": self.tag, "capabilities": list(self.capabilities), "status": self.status}


@dataclass(frozen=True)
class CloseoutSummary:
    summary_id: str
    created_at: str
    stages: tuple[StageRecord, ...]
    overall_status: str
    def to_dict(self) -> dict:
        return {"summary_id": self.summary_id, "created_at": self.created_at, "stages": [s.to_dict() for s in self.stages], "overall_status": self.overall_status}


STAGES = (
    StageRecord("STG_001", "T140001-T155000", "Testnet Submit Enablement Review", "7ca5eea", "", ("ENABLEMENT_REVIEW_READY", "READINESS_POLICY_READY", "FREEZE_PACKET_READY"), "COMPLETE"),
    StageRecord("STG_002", "T155001-T170000", "External Testnet Adapter Spec", "54b73e5", "external-testnet-adapter-spec-complete", ("ADAPTER_SPEC_READY", "CREDENTIAL_VAULT_ARCH_READY", "REQUEST_SIGNING_READY", "NETWORK_TRANSPORT_READY"), "COMPLETE"),
    StageRecord("STG_003", "T170001-T185000", "Mock Transport / Vault Stub / Field-Test Governance", "712db6e", "external-testnet-mock-transport-complete", ("MOCK_TRANSPORT_READY", "VAULT_STUB_READY", "ADAPTER_SKELETON_READY", "FIELD_TEST_GOVERNANCE_READY"), "COMPLETE"),
    StageRecord("STG_004", "T185001-T200000", "Mock Replay Harness / Evidence Bundle / Approval Packet v3", "65c5a13", "external-testnet-mock-replay-complete", ("MOCK_REPLAY_READY", "EVIDENCE_BUNDLE_READY", "APPROVAL_PACKET_V3_READY", "TRACE_VALIDATOR_READY"), "COMPLETE"),
    StageRecord("STG_005", "T200001-T215000", "Mock Review Browser / Approval Comparator / Operator Index", "f95955e", "external-testnet-mock-review-complete", ("EVIDENCE_BROWSER_READY", "APPROVAL_COMPARATOR_READY", "OPERATOR_REVIEW_INDEX_READY", "NAVIGATION_REPORT_READY"), "COMPLETE"),
)


def create_summary() -> CloseoutSummary:
    return CloseoutSummary(
        summary_id=f"CLS_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        stages=STAGES,
        overall_status="MOCK_REVIEW_CLOSEOUT_READY",
    )


def write_summary(summary: CloseoutSummary, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")


def render_report(summary: CloseoutSummary) -> str:
    lines = ["# Mock Review Closeout Summary", "",
        f"**summary_id={summary.summary_id}**",
        f"**overall_status={summary.overall_status}**",
        "**REAL_TRADING_NOT_ALLOWED**",
        "**TESTNET_SUBMIT_NOT_ALLOWED**", "",
        "## Stage Timeline", "",
        "| Milestone | Title | Commit | Tag | Status |",
        "|-----------|-------|--------|-----|--------|"]
    for s in summary.stages:
        tag = s.tag or "(pending)"
        lines.append(f"| {s.milestone} | {s.title} | {s.commit} | {tag} | {s.status} |")
    lines.extend(["", "## Capabilities Achieved", ""])
    for s in summary.stages:
        lines.append(f"### {s.milestone}")
        for cap in s.capabilities:
            lines.append(f"- {cap}")
        lines.append("")
    lines.extend(["## Conclusion", "",
        "MOCK_REVIEW_CLOSEOUT_READY",
        "REAL_TRADING_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
