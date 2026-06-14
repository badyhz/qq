"""Final no-submit archive."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ArchiveEntry:
    entry_id: str
    category: str
    title: str
    content: str
    def to_dict(self) -> dict:
        return {"entry_id": self.entry_id, "category": self.category, "title": self.title, "content": self.content}


@dataclass(frozen=True)
class FinalNoSubmitArchive:
    archive_id: str
    created_at: str
    entries: tuple[ArchiveEntry, ...]
    def to_dict(self) -> dict:
        return {"archive_id": self.archive_id, "created_at": self.created_at, "entries": [e.to_dict() for e in self.entries]}


ENTRIES = (
    ArchiveEntry("ARC_001", "timeline", "Stage Timeline", "T140001-T155000 enablement review -> T155001-T170000 adapter spec -> T170001-T185000 mock transport -> T185001-T200000 mock replay -> T200001-T215000 mock review -> T215001-T230000 closeout"),
    ArchiveEntry("ARC_002", "commits", "Commit History", "7ca5eea enablement, 54b73e5 adapter-spec, 712db6e mock-transport, 65c5a13 mock-replay, f95955e mock-review"),
    ArchiveEntry("ARC_003", "tags", "Tag List", "external-testnet-adapter-spec-complete, external-testnet-mock-transport-complete, external-testnet-mock-replay-complete, external-testnet-mock-review-complete"),
    ArchiveEntry("ARC_004", "status_markers", "Status Markers", "EXTERNAL_TESTNET_MOCK_REVIEW_SUITE_PASS, MOCK_REPLAY_EVIDENCE_BROWSER_READY, APPROVAL_PACKET_COMPARATOR_READY, OPERATOR_REVIEW_INDEX_READY"),
    ArchiveEntry("ARC_005", "qa_markers", "QA Markers", "All suite runners PASS, all integration tests PASS, compileall PASS, safety regression PASS"),
    ArchiveEntry("ARC_006", "safety_markers", "Safety Markers", "No real network, no real credentials, no real submit, no gate unlock, no real adapter"),
    ArchiveEntry("ARC_007", "blocker_reference", "Blocker Ledger Reference", "gate_blocker_ledger.json: 11 blockers, all BLOCKER_ACTIVE, SUBMIT_UNLOCK_BLOCKED"),
    ArchiveEntry("ARC_008", "readiness_reference", "Readiness Scorecard Reference", "readiness_scorecard.json: MOCK_READY, REAL_TESTNET_NOT_READY, SUBMIT_UNLOCK_BLOCKED"),
    ArchiveEntry("ARC_009", "prerequisite_reference", "Next-Stage Prerequisite Reference", "next_stage_prerequisite_checklist.json: 10 prerequisites for read-only testnet discovery"),
    ArchiveEntry("ARC_010", "prohibited_actions", "Prohibited Actions", "No real ccxt, no real requests/httpx, no real API key, no real secret, no real webhook, no submit/cancel/recon unlock, no live trading"),
    ArchiveEntry("ARC_011", "final_declaration", "Final No-Submit Declaration", "FINAL_NO_SUBMIT_ARCHIVE_READY. REAL_TESTNET_SUBMIT_NOT_ALLOWED. REAL_TRADING_NOT_ALLOWED."),
)


def create_archive() -> FinalNoSubmitArchive:
    return FinalNoSubmitArchive(
        archive_id=f"ARC_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        entries=ENTRIES,
    )


def search_entries(archive: FinalNoSubmitArchive, query: str) -> list[ArchiveEntry]:
    q = query.lower()
    return [e for e in archive.entries if q in e.title.lower() or q in e.content.lower() or q in e.category.lower()]


def write_archive(archive: FinalNoSubmitArchive, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(archive.to_dict(), indent=2), encoding="utf-8")


def render_report(archive: FinalNoSubmitArchive) -> str:
    lines = ["# Final No-Submit Archive", "",
        f"**archive_id={archive.archive_id}**",
        "**FINAL_NO_SUBMIT_ARCHIVE_READY**",
        "**REAL_TESTNET_SUBMIT_NOT_ALLOWED**",
        "**REAL_TRADING_NOT_ALLOWED**", ""]
    for e in archive.entries:
        lines.extend([f"## {e.title}", "", f"**Category:** {e.category}", "", e.content, ""])
    lines.extend(["## Conclusion", "",
        "FINAL_NO_SUBMIT_ARCHIVE_READY",
        "REAL_TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_TRADING_NOT_ALLOWED",
        ""])
    return "\n".join(lines)
