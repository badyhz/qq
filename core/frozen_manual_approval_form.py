"""T16001 — Frozen Manual Approval Form builder.

Pure deterministic. No I/O. No network. No file operations on frozen files.
Reads evidence checklist, produces manual approval form templates.
No actual approval granted. All decisions are placeholders.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass, field

RELEASE_HOLD_REQUIRED = "HOLD"

FORM_TYPES: tuple[str, ...] = (
    "KEEP_FROZEN_REVIEW_FORM",
    "ARCHIVE_AFTER_BACKUP_APPROVAL_FORM",
    "DELETE_AFTER_BACKUP_APPROVAL_FORM",
    "OFFLINE_REWRITE_APPROVAL_FORM",
    "NEEDS_MORE_REVIEW_FORM",
)

MANDATORY_CONFIRMATIONS: tuple[str, ...] = (
    "I confirm this is offline-only.",
    "I confirm no file has been executed.",
    "I confirm no file has been imported.",
    "I confirm no file has been copied by automation.",
    "I confirm no file has been moved by automation.",
    "I confirm no file has been deleted by automation.",
    "I confirm release_hold remains HOLD.",
    "I confirm live/testnet/runtime remains disabled.",
    "I confirm backup/archive/delete still requires separate explicit human approval.",
)

FORBIDDEN_CONFIRMATIONS: tuple[str, ...] = (
    "approve_live_activation",
    "approve_testnet_activation",
    "approve_runtime_activation",
    "approve_immediate_delete",
    "approve_immediate_move",
    "approve_automated_backup",
    "approve_automated_archive",
)


@dataclass(frozen=True)
class ManualApprovalForm:
    """Single manual approval form template."""
    form_id: str
    path: str
    form_type: str
    reviewer_name: str
    reviewer_role: str
    review_date: str
    candidate_action: str
    required_evidence_ids: list[str]
    required_evidence_paths: list[str]
    original_sha256: str
    original_size_bytes: int
    proposed_backup_path: str
    proposed_archive_path: str
    rollback_plan_id: str
    human_decision_placeholder: str
    decision_reason_placeholder: str
    approval_conditions: list[str]
    rejection_conditions: list[str]
    mandatory_confirmations: list[str]
    forbidden_confirmations: list[str]
    signature_placeholder: str
    release_hold: str
    advisory_only: bool
    human_review_required: bool

    def to_dict(self) -> dict:
        return {
            "form_id": self.form_id,
            "path": self.path,
            "form_type": self.form_type,
            "reviewer_name": self.reviewer_name,
            "reviewer_role": self.reviewer_role,
            "review_date": self.review_date,
            "candidate_action": self.candidate_action,
            "required_evidence_ids": self.required_evidence_ids,
            "required_evidence_paths": self.required_evidence_paths,
            "original_sha256": self.original_sha256,
            "original_size_bytes": self.original_size_bytes,
            "proposed_backup_path": self.proposed_backup_path,
            "proposed_archive_path": self.proposed_archive_path,
            "rollback_plan_id": self.rollback_plan_id,
            "human_decision_placeholder": self.human_decision_placeholder,
            "decision_reason_placeholder": self.decision_reason_placeholder,
            "approval_conditions": self.approval_conditions,
            "rejection_conditions": self.rejection_conditions,
            "mandatory_confirmations": self.mandatory_confirmations,
            "forbidden_confirmations": self.forbidden_confirmations,
            "signature_placeholder": self.signature_placeholder,
            "release_hold": self.release_hold,
            "advisory_only": self.advisory_only,
            "human_review_required": self.human_review_required,
        }


def _safe_id(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(".", "_")


def _form_type(candidate_action: str) -> str:
    mapping = {
        "KEEP_FROZEN": "KEEP_FROZEN_REVIEW_FORM",
        "PREPARE_ARCHIVE_AFTER_BACKUP": "ARCHIVE_AFTER_BACKUP_APPROVAL_FORM",
        "PREPARE_DELETE_AFTER_BACKUP": "DELETE_AFTER_BACKUP_APPROVAL_FORM",
        "PREPARE_OFFLINE_REWRITE": "OFFLINE_REWRITE_APPROVAL_FORM",
        "NEEDS_MORE_REVIEW": "NEEDS_MORE_REVIEW_FORM",
    }
    return mapping.get(candidate_action, "NEEDS_MORE_REVIEW_FORM")


def _approval_conditions(candidate_action: str) -> list[str]:
    base = [
        "all_evidence_collected",
        "hash_independently_verified",
        "rollback_plan_reviewed",
        "human_owner_assigned",
        "release_hold_remains_HOLD",
    ]
    if candidate_action in ("PREPARE_ARCHIVE_AFTER_BACKUP", "PREPARE_DELETE_AFTER_BACKUP"):
        base.append("backup_completed_and_verified")
    if candidate_action == "PREPARE_OFFLINE_REWRITE":
        base.append("rewrite_plan_reviewed")
    return base


def _rejection_conditions() -> list[str]:
    return [
        "evidence_incomplete",
        "hash_mismatch",
        "rollback_plan_missing",
        "owner_not_assigned",
        "release_hold_not_HOLD",
        "insufficient_review",
    ]


def build_form_from_checklist_item(
    checklist_item: dict,
    release_hold: str,
) -> ManualApprovalForm:
    """Build a single approval form from a checklist item."""
    path = checklist_item["path"]
    safe_id = _safe_id(path)
    candidate_action = checklist_item.get("candidate_action", "KEEP_FROZEN")

    return ManualApprovalForm(
        form_id=f"approval_form_{safe_id}",
        path=path,
        form_type=_form_type(candidate_action),
        reviewer_name="PENDING_HUMAN_REVIEWER",
        reviewer_role="PENDING_HUMAN_ROLE",
        review_date="PENDING_HUMAN_DATE",
        candidate_action=candidate_action,
        required_evidence_ids=checklist_item.get("required_evidence", []),
        required_evidence_paths=checklist_item.get("evidence_paths_placeholder", []),
        original_sha256=_extract_hash(checklist_item),
        original_size_bytes=_extract_size(checklist_item),
        proposed_backup_path=f"archive_simulation/frozen_files/{safe_id}",
        proposed_archive_path=f"archive_simulation/archived/{safe_id}",
        rollback_plan_id=checklist_item.get("required_rollback_note", ""),
        human_decision_placeholder="PENDING_HUMAN_DECISION",
        decision_reason_placeholder="PENDING_HUMAN_REASON",
        approval_conditions=_approval_conditions(candidate_action),
        rejection_conditions=_rejection_conditions(),
        mandatory_confirmations=list(MANDATORY_CONFIRMATIONS),
        forbidden_confirmations=list(FORBIDDEN_CONFIRMATIONS),
        signature_placeholder="PENDING_HUMAN_SIGNATURE",
        release_hold=release_hold,
        advisory_only=True,
        human_review_required=True,
    )


def _extract_hash(item: dict) -> str:
    for ev in item.get("required_hash_evidence", []):
        if ev.startswith("known_hash="):
            return ev[len("known_hash="):]
    return ""


def _extract_size(item: dict) -> int:
    for ev in item.get("required_size_evidence", []):
        if ev.startswith("known_size="):
            try:
                return int(ev[len("known_size="):].replace("_bytes", ""))
            except ValueError:
                pass
    return 0


def build_manual_approval_forms(
    checklist_items: list[dict],
    release_hold: str = RELEASE_HOLD_REQUIRED,
) -> list[ManualApprovalForm]:
    """Build all manual approval forms from evidence checklist."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    return [
        build_form_from_checklist_item(ci, release_hold)
        for ci in checklist_items
    ]


def compute_forms_hash(forms: list[ManualApprovalForm]) -> str:
    raw = json.dumps([f.to_dict() for f in forms], sort_keys=True, indent=2)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def render_forms_markdown(forms: list[ManualApprovalForm]) -> str:
    lines = [
        "# Frozen File Manual Approval Forms",
        "",
        f"**Total forms:** {len(forms)}",
        f"**release_hold:** HOLD",
        f"**advisory_only:** true",
        f"**human_review_required:** true",
        "",
        "## Safety Boundary",
        "",
        "- All decisions are placeholders.",
        "- No form grants immediate delete/move/copy/archive.",
        "- No form approves live/testnet/runtime activation.",
        "- release_hold=HOLD for all forms.",
        "",
        "## Mandatory Confirmations",
        "",
    ]
    for mc in MANDATORY_CONFIRMATIONS:
        lines.append(f"- {mc}")
    lines.append("")

    lines.append("## Forbidden Confirmations")
    lines.append("")
    for fc in FORBIDDEN_CONFIRMATIONS:
        lines.append(f"- **FORBIDDEN:** {fc}")
    lines.append("")

    lines.append("## Approval Forms")
    lines.append("")

    for form in forms:
        lines.append(f"### {form.path}")
        lines.append("")
        lines.append(f"- **form_id:** {form.form_id}")
        lines.append(f"- **form_type:** {form.form_type}")
        lines.append(f"- **candidate_action:** {form.candidate_action}")
        lines.append(f"- **reviewer_name:** {form.reviewer_name}")
        lines.append(f"- **human_decision:** {form.human_decision_placeholder}")
        lines.append(f"- **release_hold:** {form.release_hold}")
        lines.append("")
        lines.append("**Approval Conditions:**")
        for ac in form.approval_conditions:
            lines.append(f"  - {ac}")
        lines.append("")
        lines.append("**Rejection Conditions:**")
        for rc in form.rejection_conditions:
            lines.append(f"  - {rc}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def load_checklist_items(path: pathlib.Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("items", [])


def write_json(forms: list[ManualApprovalForm], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([f.to_dict() for f in forms], indent=2, sort_keys=False),
        encoding="utf-8",
    )


def write_manifest(
    forms: list[ManualApprovalForm],
    out_path: pathlib.Path,
    release_hold: str,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    form_type_counts: dict[str, int] = {}
    for form in forms:
        form_type_counts[form.form_type] = form_type_counts.get(form.form_type, 0) + 1
    manifest = {
        "total_forms": len(forms),
        "form_type_counts": form_type_counts,
        "release_hold": release_hold,
        "all_decisions_placeholders": all(
            f.human_decision_placeholder == "PENDING_HUMAN_DECISION" for f in forms
        ),
        "no_immediate_action_granted": True,
        "advisory_only": True,
        "human_review_required": True,
        "forms_hash": compute_forms_hash(forms),
    }
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_markdown(forms: list[ManualApprovalForm], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_forms_markdown(forms), encoding="utf-8")
