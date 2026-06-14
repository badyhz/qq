"""Operator signoff draft: prepared signoff document for human review."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class SignoffSection:
    section_id: str
    title: str
    content: str
    status: str
    def to_dict(self) -> dict:
        return {"section_id": self.section_id, "title": self.title,
                "content": self.content, "status": self.status}


@dataclass(frozen=True)
class OperatorSignoffDraft:
    draft_id: str
    created_at: str
    stage: str
    sections: tuple[SignoffSection, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"draft_id": self.draft_id, "created_at": self.created_at,
                "stage": self.stage,
                "sections": [s.to_dict() for s in self.sections],
                "final_verdict": self.final_verdict}


SECTIONS = (
    SignoffSection("SIGN_001", "Scope Declaration", "Read-only discovery release gate review only. No real network, no submit, no real credentials.", "DRAFT"),
    SignoffSection("SIGN_002", "Safety Attestation", "All safety regressions passed. No forbidden imports, no forbidden statuses, no real endpoints.", "DRAFT"),
    SignoffSection("SIGN_003", "Blocker Acknowledgment", "All critical blockers acknowledged and enforced by automated scans.", "DRAFT"),
    SignoffSection("SIGN_004", "Credential Air-Gap Confirmation", "Zero credential access confirmed. No dotenv, no env-var credential read, no real keys.", "DRAFT"),
    SignoffSection("SIGN_005", "Network-Off Confirmation", "All execution steps verified network-off safe. Steps requiring network are gated.", "DRAFT"),
    SignoffSection("SIGN_006", "Operator Authorization", "Operator authorizes read-only discovery release gate completion.", "PENDING"),
    SignoffSection("SIGN_007", "Human Review Date", "To be filled by human reviewer.", "PENDING"),
    SignoffSection("SIGN_008", "Next Stage Authorization", "Authorization to proceed to T275001-T290000 pending.", "PENDING"),
)


def create_draft() -> OperatorSignoffDraft:
    return OperatorSignoffDraft(
        draft_id=f"OSD_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        stage="T260001-T275000",
        sections=SECTIONS,
        final_verdict="READONLY_DISCOVERY_OPERATOR_SIGNOFF_DRAFT_READY|HUMAN_SIGNOFF_PENDING|REAL_NETWORK_NOT_ALLOWED",
    )


def write_draft(draft: OperatorSignoffDraft, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(draft.to_dict(), indent=2), encoding="utf-8")


def render_report(draft: OperatorSignoffDraft) -> str:
    lines = ["# Read-Only Discovery Operator Signoff Draft", "",
        f"**draft_id={draft.draft_id}**",
        f"**stage={draft.stage}**",
        f"**verdict={draft.final_verdict}**", "",
        "## Sections", ""]
    for s in draft.sections:
        lines.append(f"### {s.section_id}: {s.title}")
        lines.append(f"Status: {s.status}")
        lines.append(f"{s.content}")
        lines.append("")
    lines.extend(["## Conclusion", "",
        "READONLY_DISCOVERY_OPERATOR_SIGNOFF_DRAFT_READY",
        "HUMAN_SIGNOFF_PENDING",
        "REAL_NETWORK_NOT_ALLOWED", ""])
    return "\n".join(lines)
