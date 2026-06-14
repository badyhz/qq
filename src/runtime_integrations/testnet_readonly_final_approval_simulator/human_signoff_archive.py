"""Human signoff archive: stores completed signoff records for audit trail."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class SignoffRecord:
    record_id: str
    phase: str
    signatory: str
    decision: str
    timestamp: str
    notes: str
    def to_dict(self) -> dict:
        return {"record_id": self.record_id, "phase": self.phase,
                "signatory": self.signatory, "decision": self.decision,
                "timestamp": self.timestamp, "notes": self.notes}


@dataclass(frozen=True)
class HumanSignoffArchive:
    archive_id: str
    created_at: str
    records: tuple[SignoffRecord, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"archive_id": self.archive_id, "created_at": self.created_at,
                "records": [r.to_dict() for r in self.records],
                "final_verdict": self.final_verdict}


RECORDS = (
    SignoffRecord("SO_001", "Mock Transport", "PLACEHOLDER_OPERATOR", "APPROVED", "SIMULATED_TIMESTAMP", "Mock transport layer verified"),
    SignoffRecord("SO_002", "Mock Replay", "PLACEHOLDER_OPERATOR", "APPROVED", "SIMULATED_TIMESTAMP", "Mock replay evidence verified"),
    SignoffRecord("SO_003", "Mock Review", "PLACEHOLDER_OPERATOR", "APPROVED", "SIMULATED_TIMESTAMP", "Mock review browser verified"),
    SignoffRecord("SO_004", "Mock Closeout", "PLACEHOLDER_OPERATOR", "APPROVED", "SIMULATED_TIMESTAMP", "Mock closeout archive verified"),
    SignoffRecord("SO_005", "Read-Only Discovery", "PLACEHOLDER_OPERATOR", "APPROVED", "SIMULATED_TIMESTAMP", "Discovery design layer verified"),
    SignoffRecord("SO_006", "Read-Only Preapproval", "PLACEHOLDER_OPERATOR", "APPROVED", "SIMULATED_TIMESTAMP", "Preapproval evidence pack verified"),
    SignoffRecord("SO_007", "Release Gate", "PLACEHOLDER_OPERATOR", "APPROVED", "SIMULATED_TIMESTAMP", "Release gate packet verified"),
    SignoffRecord("SO_008", "Final Approval", "PLACEHOLDER_OPERATOR", "SIMULATED", "SIMULATED_TIMESTAMP", "Final approval simulated, awaiting real human signoff"),
)


def create_archive() -> HumanSignoffArchive:
    return HumanSignoffArchive(
        archive_id=f"HSA_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        records=RECORDS,
        final_verdict="READONLY_HUMAN_SIGNOFF_ARCHIVE_READY|ALL_PHASES_DOCUMENTED|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_archive(archive: HumanSignoffArchive, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(archive.to_dict(), indent=2), encoding="utf-8")


def render_report(archive: HumanSignoffArchive) -> str:
    lines = ["# Human Signoff Archive", "",
        f"**archive_id={archive.archive_id}**",
        f"**verdict={archive.final_verdict}**", "",
        "## Signoff Records", "",
        "| Record | Phase | Signatory | Decision | Notes |",
        "|--------|-------|-----------|----------|-------|"]
    for r in archive.records:
        lines.append(f"| {r.record_id} | {r.phase} | {r.signatory} | {r.decision} | {r.notes} |")
    lines.extend(["", "## Conclusion", "",
        "READONLY_HUMAN_SIGNOFF_ARCHIVE_READY",
        "ALL_PHASES_DOCUMENTED",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
