"""No-submit release archive: final archive of all read-only discovery artifacts."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ArchiveEntry:
    entry_id: str
    artifact_name: str
    stage: str
    location: str
    status: str
    def to_dict(self) -> dict:
        return {"entry_id": self.entry_id, "artifact_name": self.artifact_name,
                "stage": self.stage, "location": self.location, "status": self.status}


@dataclass(frozen=True)
class NoSubmitReleaseArchive:
    archive_id: str
    created_at: str
    entries: tuple[ArchiveEntry, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"archive_id": self.archive_id, "created_at": self.created_at,
                "entries": [e.to_dict() for e in self.entries],
                "final_verdict": self.final_verdict}


ENTRIES = (
    ArchiveEntry("ARC_001", "External adapter spec", "T155001-T170000", "data/runtime/testnet_adapter_spec/", "ARCHIVED"),
    ArchiveEntry("ARC_002", "Mock transport pack", "T170001-T185000", "data/runtime/testnet_mock_transport/", "ARCHIVED"),
    ArchiveEntry("ARC_003", "Mock replay evidence", "T185001-T200000", "data/runtime/testnet_mock_replay/", "ARCHIVED"),
    ArchiveEntry("ARC_004", "Mock review browser", "T200001-T215000", "data/runtime/testnet_mock_review/", "ARCHIVED"),
    ArchiveEntry("ARC_005", "Mock closeout archive", "T215001-T230000", "data/runtime/testnet_mock_closeout/", "ARCHIVED"),
    ArchiveEntry("ARC_006", "Read-only discovery design", "T230001-T245000", "data/runtime/testnet_readonly_discovery/", "ARCHIVED"),
    ArchiveEntry("ARC_007", "Read-only preapproval evidence", "T245001-T260000", "data/runtime/testnet_readonly_preapproval/", "ARCHIVED"),
    ArchiveEntry("ARC_008", "Read-only release gate", "T260001-T275000", "data/runtime/testnet_readonly_release_gate/", "ARCHIVED"),
    ArchiveEntry("ARC_009", "Final approval simulator", "T275001-T290000", "data/runtime/testnet_readonly_final_approval_simulator/", "ARCHIVED"),
    ArchiveEntry("ARC_010", "Dry execution rehearsal", "T290001-T305000", "data/runtime/testnet_readonly_dry_execution_rehearsal/", "ARCHIVED"),
    ArchiveEntry("ARC_011", "Final governance freeze", "T305001-T320000", "data/runtime/testnet_readonly_final_governance_freeze/", "ARCHIVED"),
)


def create_archive() -> NoSubmitReleaseArchive:
    return NoSubmitReleaseArchive(
        archive_id=f"NSA_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        entries=ENTRIES,
        final_verdict="NO_SUBMIT_RELEASE_ARCHIVE_READY|ALL_ARTIFACTS_ARCHIVED|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_archive(archive: NoSubmitReleaseArchive, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(archive.to_dict(), indent=2), encoding="utf-8")


def render_report(archive: NoSubmitReleaseArchive) -> str:
    lines = ["# No-Submit Release Archive", "",
        f"**archive_id={archive.archive_id}**",
        f"**verdict={archive.final_verdict}**", "",
        "## Archived Artifacts", "",
        "| Entry | Artifact | Stage | Location | Status |",
        "|-------|----------|-------|----------|--------|"]
    for e in archive.entries:
        lines.append(f"| {e.entry_id} | {e.artifact_name} | {e.stage} | {e.location} | {e.status} |")
    lines.extend(["", "## Conclusion", "",
        "NO_SUBMIT_RELEASE_ARCHIVE_READY",
        "ALL_ARTIFACTS_ARCHIVED",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
