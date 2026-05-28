"""T16501 — Frozen Completed Form Simulation.

Pure deterministic. No I/O. No network.
Generates simulated completed approval forms from manual approval form templates.
No actual approval granted. No actual action performed. No file operations.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

RELEASE_HOLD_REQUIRED = "HOLD"

SIMULATION_CATEGORIES: tuple[str, ...] = (
    "valid_keep_frozen",
    "valid_prepare_archive_after_backup",
    "valid_prepare_delete_after_backup",
    "valid_prepare_offline_rewrite",
    "request_more_review",
    "reject",
    "missing_reviewer",
    "missing_decision",
    "forbidden_delete_now",
    "forbidden_move_now",
    "forbidden_copy_now",
    "forbidden_archive_now",
    "forbidden_execute_now",
    "forbidden_import_now",
    "forbidden_activate_live",
    "forbidden_activate_testnet",
    "forbidden_enable_runtime",
    "forbidden_enable_planner",
    "release_hold_override",
    "missing_evidence_for_archive",
    "missing_evidence_for_delete",
    "incomplete_hash_evidence",
    "incomplete_rollback_evidence",
    "conflicting_confirmations",
    "unsafe_auto_action_requested",
)

VALID_DECISIONS = (
    "KEEP_FROZEN",
    "APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP",
    "APPROVE_PREPARE_DELETE_AFTER_BACKUP",
    "APPROVE_PREPARE_OFFLINE_REWRITE",
    "REQUEST_MORE_REVIEW",
    "REJECT",
)

FORBIDDEN_DECISIONS = (
    "DELETE_NOW",
    "MOVE_NOW",
    "COPY_NOW",
    "ARCHIVE_NOW",
    "EXECUTE_NOW",
    "IMPORT_NOW",
    "ACTIVATE_LIVE",
    "ACTIVATE_TESTNET",
    "ENABLE_RUNTIME",
    "ENABLE_PLANNER",
)


@dataclass(frozen=True)
class SimulatedForm:
    """A single simulated completed form."""
    completed_form_id: str
    source_form_id: str
    path: str
    simulation_category: str
    reviewer_name: str
    reviewer_role: str
    review_date: str
    human_decision: str
    decision_reason: str
    evidence_status: str
    evidence_ids_confirmed: list[str]
    hash_evidence_confirmed: bool
    rollback_evidence_confirmed: bool
    backup_evidence_confirmed: bool
    mandatory_confirmations_checked: list[str]
    forbidden_confirmations_checked: list[str]
    release_hold: str
    advisory_only: bool
    human_review_required: bool
    dry_run_only: bool = True
    action_requested: bool = False
    no_action_performed: bool = True

    def to_dict(self) -> dict:
        return {
            "completed_form_id": self.completed_form_id,
            "source_form_id": self.source_form_id,
            "path": self.path,
            "simulation_category": self.simulation_category,
            "reviewer_name": self.reviewer_name,
            "reviewer_role": self.reviewer_role,
            "review_date": self.review_date,
            "human_decision": self.human_decision,
            "decision_reason": self.decision_reason,
            "evidence_status": self.evidence_status,
            "evidence_ids_confirmed": list(self.evidence_ids_confirmed),
            "hash_evidence_confirmed": self.hash_evidence_confirmed,
            "rollback_evidence_confirmed": self.rollback_evidence_confirmed,
            "backup_evidence_confirmed": self.backup_evidence_confirmed,
            "mandatory_confirmations_checked": list(self.mandatory_confirmations_checked),
            "forbidden_confirmations_checked": list(self.forbidden_confirmations_checked),
            "release_hold": self.release_hold,
            "advisory_only": self.advisory_only,
            "human_review_required": self.human_review_required,
            "dry_run_only": self.dry_run_only,
            "action_requested": self.action_requested,
            "no_action_performed": self.no_action_performed,
        }


@dataclass(frozen=True)
class SimulationResult:
    """Full simulation result."""
    simulations: list[SimulatedForm]
    total_count: int
    category_counts: dict[str, int]
    release_hold: str
    dry_run_only: bool = True
    action_requested: bool = False
    no_action_performed: bool = True

    def to_dict(self) -> dict:
        return {
            "simulations": [s.to_dict() for s in self.simulations],
            "total_count": self.total_count,
            "category_counts": dict(sorted(self.category_counts.items())),
            "release_hold": self.release_hold,
            "dry_run_only": self.dry_run_only,
            "action_requested": self.action_requested,
            "no_action_performed": self.no_action_performed,
        }


def _make_valid_keep_frozen(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_valid_keep_frozen",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="valid_keep_frozen",
        reviewer_name="Dr. Alice Reviewer",
        reviewer_role="Senior Analyst",
        review_date="2026-05-29",
        human_decision="KEEP_FROZEN",
        decision_reason="File should remain frozen until further review.",
        evidence_status="COMPLETE_FOR_HUMAN_REVIEW",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", [])),
        hash_evidence_confirmed=True,
        rollback_evidence_confirmed=True,
        backup_evidence_confirmed=True,
        mandatory_confirmations_checked=list(form.get("mandatory_confirmations", [])),
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_valid_prepare_archive(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_valid_prepare_archive",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="valid_prepare_archive_after_backup",
        reviewer_name="Bob Archive Reviewer",
        reviewer_role="Risk Officer",
        review_date="2026-05-29",
        human_decision="APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP",
        decision_reason="All evidence collected. Prepare archive after backup only.",
        evidence_status="COMPLETE_FOR_HUMAN_REVIEW",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", [])),
        hash_evidence_confirmed=True,
        rollback_evidence_confirmed=True,
        backup_evidence_confirmed=True,
        mandatory_confirmations_checked=list(form.get("mandatory_confirmations", [])),
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_valid_prepare_delete(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_valid_prepare_delete",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="valid_prepare_delete_after_backup",
        reviewer_name="Carol Delete Reviewer",
        reviewer_role="Compliance Officer",
        review_date="2026-05-29",
        human_decision="APPROVE_PREPARE_DELETE_AFTER_BACKUP",
        decision_reason="All evidence collected. Prepare delete after backup only.",
        evidence_status="COMPLETE_FOR_HUMAN_REVIEW",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", [])),
        hash_evidence_confirmed=True,
        rollback_evidence_confirmed=True,
        backup_evidence_confirmed=True,
        mandatory_confirmations_checked=list(form.get("mandatory_confirmations", [])),
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_valid_prepare_offline_rewrite(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_valid_prepare_offline_rewrite",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="valid_prepare_offline_rewrite",
        reviewer_name="Dave Rewrite Reviewer",
        reviewer_role="Technical Lead",
        review_date="2026-05-29",
        human_decision="APPROVE_PREPARE_OFFLINE_REWRITE",
        decision_reason="All evidence collected. Prepare offline rewrite only.",
        evidence_status="COMPLETE_FOR_HUMAN_REVIEW",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", [])),
        hash_evidence_confirmed=True,
        rollback_evidence_confirmed=True,
        backup_evidence_confirmed=True,
        mandatory_confirmations_checked=list(form.get("mandatory_confirmations", [])),
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_request_more_review(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_request_more_review",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="request_more_review",
        reviewer_name="Eve Escalation Reviewer",
        reviewer_role="Audit Lead",
        review_date="2026-05-29",
        human_decision="REQUEST_MORE_REVIEW",
        decision_reason="Need additional review before any disposition.",
        evidence_status="PARTIAL",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", []))[:5],
        hash_evidence_confirmed=True,
        rollback_evidence_confirmed=False,
        backup_evidence_confirmed=False,
        mandatory_confirmations_checked=list(form.get("mandatory_confirmations", [])),
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_reject(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_reject",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="reject",
        reviewer_name="Frank Reject Reviewer",
        reviewer_role="Governance Officer",
        review_date="2026-05-29",
        human_decision="REJECT",
        decision_reason="Insufficient justification for any action.",
        evidence_status="PARTIAL",
        evidence_ids_confirmed=[],
        hash_evidence_confirmed=False,
        rollback_evidence_confirmed=False,
        backup_evidence_confirmed=False,
        mandatory_confirmations_checked=[],
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_missing_reviewer(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_missing_reviewer",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="missing_reviewer",
        reviewer_name="",
        reviewer_role="",
        review_date="",
        human_decision="KEEP_FROZEN",
        decision_reason="Decision made but reviewer not recorded.",
        evidence_status="COMPLETE_FOR_HUMAN_REVIEW",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", [])),
        hash_evidence_confirmed=True,
        rollback_evidence_confirmed=True,
        backup_evidence_confirmed=True,
        mandatory_confirmations_checked=list(form.get("mandatory_confirmations", [])),
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_missing_decision(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_missing_decision",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="missing_decision",
        reviewer_name="Grace Incomplete Reviewer",
        reviewer_role="Analyst",
        review_date="2026-05-29",
        human_decision="",
        decision_reason="",
        evidence_status="PARTIAL",
        evidence_ids_confirmed=[],
        hash_evidence_confirmed=False,
        rollback_evidence_confirmed=False,
        backup_evidence_confirmed=False,
        mandatory_confirmations_checked=[],
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_forbidden_decision(form: dict, idx: int, category: str, decision: str) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_{category}",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category=category,
        reviewer_name="Hank Forbidden Reviewer",
        reviewer_role="Unauthorized Actor",
        review_date="2026-05-29",
        human_decision=decision,
        decision_reason=f"I want to {decision.lower().replace('_', ' ')} immediately.",
        evidence_status="COMPLETE_FOR_HUMAN_REVIEW",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", [])),
        hash_evidence_confirmed=True,
        rollback_evidence_confirmed=True,
        backup_evidence_confirmed=True,
        mandatory_confirmations_checked=list(form.get("mandatory_confirmations", [])),
        forbidden_confirmations_checked=list(form.get("forbidden_confirmations", [])),
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_release_hold_override(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_release_hold_override",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="release_hold_override",
        reviewer_name="Ivy Override Reviewer",
        reviewer_role="Unauthorized Actor",
        review_date="2026-05-29",
        human_decision="KEEP_FROZEN",
        decision_reason="Trying to override release hold.",
        evidence_status="COMPLETE_FOR_HUMAN_REVIEW",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", [])),
        hash_evidence_confirmed=True,
        rollback_evidence_confirmed=True,
        backup_evidence_confirmed=True,
        mandatory_confirmations_checked=list(form.get("mandatory_confirmations", [])),
        forbidden_confirmations_checked=[],
        release_hold="RELEASED",
        advisory_only=True,
        human_review_required=True,
    )


def _make_missing_evidence_archive(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_missing_evidence_archive",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="missing_evidence_for_archive",
        reviewer_name="Jack Evidence Reviewer",
        reviewer_role="Risk Analyst",
        review_date="2026-05-29",
        human_decision="APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP",
        decision_reason="Want to archive but evidence incomplete.",
        evidence_status="PENDING",
        evidence_ids_confirmed=[],
        hash_evidence_confirmed=False,
        rollback_evidence_confirmed=False,
        backup_evidence_confirmed=False,
        mandatory_confirmations_checked=[],
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_missing_evidence_delete(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_missing_evidence_delete",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="missing_evidence_for_delete",
        reviewer_name="Kate Delete Evidence Reviewer",
        reviewer_role="Risk Analyst",
        review_date="2026-05-29",
        human_decision="APPROVE_PREPARE_DELETE_AFTER_BACKUP",
        decision_reason="Want to delete but evidence incomplete.",
        evidence_status="PENDING",
        evidence_ids_confirmed=[],
        hash_evidence_confirmed=False,
        rollback_evidence_confirmed=False,
        backup_evidence_confirmed=False,
        mandatory_confirmations_checked=[],
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_incomplete_hash(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_incomplete_hash",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="incomplete_hash_evidence",
        reviewer_name="Leo Hash Reviewer",
        reviewer_role="Technical Auditor",
        review_date="2026-05-29",
        human_decision="APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP",
        decision_reason="Hash evidence not fully confirmed.",
        evidence_status="PARTIAL",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", []))[:3],
        hash_evidence_confirmed=False,
        rollback_evidence_confirmed=True,
        backup_evidence_confirmed=True,
        mandatory_confirmations_checked=list(form.get("mandatory_confirmations", [])),
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_incomplete_rollback(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_incomplete_rollback",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="incomplete_rollback_evidence",
        reviewer_name="Mona Rollback Reviewer",
        reviewer_role="Technical Auditor",
        review_date="2026-05-29",
        human_decision="APPROVE_PREPARE_DELETE_AFTER_BACKUP",
        decision_reason="Rollback evidence not fully confirmed.",
        evidence_status="PARTIAL",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", []))[:3],
        hash_evidence_confirmed=True,
        rollback_evidence_confirmed=False,
        backup_evidence_confirmed=True,
        mandatory_confirmations_checked=list(form.get("mandatory_confirmations", [])),
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_conflicting_confirmations(form: dict, idx: int) -> SimulatedForm:
    mandatory = list(form.get("mandatory_confirmations", []))
    forbidden = list(form.get("forbidden_confirmations", []))
    # Simulate conflict: a forbidden confirmation also checked as mandatory
    conflicting = forbidden[:1] if forbidden else []
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_conflicting_confirmations",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="conflicting_confirmations",
        reviewer_name="Nora Conflict Reviewer",
        reviewer_role="Compliance Analyst",
        review_date="2026-05-29",
        human_decision="KEEP_FROZEN",
        decision_reason="Conflicting confirmations checked.",
        evidence_status="COMPLETE_FOR_HUMAN_REVIEW",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", [])),
        hash_evidence_confirmed=True,
        rollback_evidence_confirmed=True,
        backup_evidence_confirmed=True,
        mandatory_confirmations_checked=mandatory + conflicting,
        forbidden_confirmations_checked=conflicting,
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
    )


def _make_unsafe_auto_action(form: dict, idx: int) -> SimulatedForm:
    return SimulatedForm(
        completed_form_id=f"completed_{form['form_id']}_unsafe_auto_action",
        source_form_id=form["form_id"],
        path=form["path"],
        simulation_category="unsafe_auto_action_requested",
        reviewer_name="Oscar Unsafe Reviewer",
        reviewer_role="Automation Script",
        review_date="2026-05-29",
        human_decision="KEEP_FROZEN",
        decision_reason="Automated action requested.",
        evidence_status="COMPLETE_FOR_HUMAN_REVIEW",
        evidence_ids_confirmed=list(form.get("required_evidence_ids", [])),
        hash_evidence_confirmed=True,
        rollback_evidence_confirmed=True,
        backup_evidence_confirmed=True,
        mandatory_confirmations_checked=list(form.get("mandatory_confirmations", [])),
        forbidden_confirmations_checked=[],
        release_hold=RELEASE_HOLD_REQUIRED,
        advisory_only=True,
        human_review_required=True,
        action_requested=True,
    )


def _build_category_forbidden(form: dict, idx: int) -> list[SimulatedForm]:
    """Build all forbidden-decision simulations for a form."""
    mapping = [
        ("forbidden_delete_now", "DELETE_NOW"),
        ("forbidden_move_now", "MOVE_NOW"),
        ("forbidden_copy_now", "COPY_NOW"),
        ("forbidden_archive_now", "ARCHIVE_NOW"),
        ("forbidden_execute_now", "EXECUTE_NOW"),
        ("forbidden_import_now", "IMPORT_NOW"),
        ("forbidden_activate_live", "ACTIVATE_LIVE"),
        ("forbidden_activate_testnet", "ACTIVATE_TESTNET"),
        ("forbidden_enable_runtime", "ENABLE_RUNTIME"),
        ("forbidden_enable_planner", "ENABLE_PLANNER"),
    ]
    return [_make_forbidden_decision(form, idx, cat, dec) for cat, dec in mapping]


def generate_simulations(forms: list[dict], release_hold: str = RELEASE_HOLD_REQUIRED) -> SimulationResult:
    """Generate all simulated completed forms from manual approval form templates."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    simulations: list[SimulatedForm] = []

    for idx, form in enumerate(forms):
        # Valid categories (one per form, cycling through the 4 valid types)
        simulations.append(_make_valid_keep_frozen(form, idx))
        simulations.append(_make_valid_prepare_archive(form, idx))
        simulations.append(_make_valid_prepare_delete(form, idx))
        simulations.append(_make_valid_prepare_offline_rewrite(form, idx))
        # Other non-forbidden
        simulations.append(_make_request_more_review(form, idx))
        simulations.append(_make_reject(form, idx))
        simulations.append(_make_missing_reviewer(form, idx))
        simulations.append(_make_missing_decision(form, idx))
        # All 10 forbidden decisions
        simulations.extend(_build_category_forbidden(form, idx))
        # Release hold override
        simulations.append(_make_release_hold_override(form, idx))
        # Evidence issues
        simulations.append(_make_missing_evidence_archive(form, idx))
        simulations.append(_make_missing_evidence_delete(form, idx))
        simulations.append(_make_incomplete_hash(form, idx))
        simulations.append(_make_incomplete_rollback(form, idx))
        # Conflicting and unsafe
        simulations.append(_make_conflicting_confirmations(form, idx))
        simulations.append(_make_unsafe_auto_action(form, idx))

    # Count categories
    cat_counts: dict[str, int] = {}
    for s in simulations:
        cat_counts[s.simulation_category] = cat_counts.get(s.simulation_category, 0) + 1

    return SimulationResult(
        simulations=simulations,
        total_count=len(simulations),
        category_counts=cat_counts,
        release_hold=release_hold,
    )


def render_simulation_markdown(result: SimulationResult) -> str:
    """Render simulation result as markdown."""
    lines = [
        "# Frozen Completed Form Simulations",
        "",
        f"**Total simulations:** {result.total_count}",
        f"**release_hold:** {result.release_hold}",
        f"**dry_run_only:** {result.dry_run_only}",
        f"**action_requested:** {result.action_requested}",
        f"**no_action_performed:** {result.no_action_performed}",
        "",
        "## Category Counts",
        "",
    ]
    for cat, count in sorted(result.category_counts.items()):
        lines.append(f"- **{cat}:** {count}")

    lines.append("")
    lines.append("## Simulated Forms")
    lines.append("")
    for s in result.simulations:
        lines.append(f"### {s.completed_form_id}")
        lines.append(f"- **source:** {s.source_form_id}")
        lines.append(f"- **path:** {s.path}")
        lines.append(f"- **category:** {s.simulation_category}")
        lines.append(f"- **reviewer:** {s.reviewer_name} ({s.reviewer_role})")
        lines.append(f"- **decision:** {s.human_decision}")
        lines.append(f"- **reason:** {s.decision_reason}")
        lines.append(f"- **evidence_status:** {s.evidence_status}")
        lines.append(f"- **hash_confirmed:** {s.hash_evidence_confirmed}")
        lines.append(f"- **rollback_confirmed:** {s.rollback_evidence_confirmed}")
        lines.append(f"- **backup_confirmed:** {s.backup_evidence_confirmed}")
        lines.append(f"- **release_hold:** {s.release_hold}")
        lines.append(f"- **dry_run_only:** {s.dry_run_only}")
        lines.append(f"- **action_requested:** {s.action_requested}")
        lines.append(f"- **no_action_performed:** {s.no_action_performed}")
        lines.append("")

    lines.append("---")
    lines.append("NO ACTION AUTHORIZED. DRY-ONLY SIMULATION.")
    lines.append("")
    return "\n".join(lines)


def render_manifest(result: SimulationResult) -> dict:
    """Render manifest for JSON output."""
    h = hashlib.sha256(
        json.dumps(result.to_dict(), sort_keys=True, indent=2).encode()
    ).hexdigest()
    return {
        "total_count": result.total_count,
        "category_counts": dict(sorted(result.category_counts.items())),
        "release_hold": result.release_hold,
        "dry_run_only": result.dry_run_only,
        "no_action_performed": result.no_action_performed,
        "simulation_hash": h,
    }
