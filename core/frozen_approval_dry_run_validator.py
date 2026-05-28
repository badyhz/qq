"""T16501 — Frozen Approval Dry-Run Validator.

Pure deterministic. No I/O. No network.
Validates simulated completed forms in dry-run mode.
No actual approval granted. No actual action performed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

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

# Outcomes
DRY_RUN_ACCEPTED_PREPARE_ONLY = "DRY_RUN_ACCEPTED_PREPARE_ONLY"
DRY_RUN_REJECTED_FORBIDDEN_DECISION = "DRY_RUN_REJECTED_FORBIDDEN_DECISION"
DRY_RUN_REJECTED_MISSING_REVIEWER = "DRY_RUN_REJECTED_MISSING_REVIEWER"
DRY_RUN_REJECTED_MISSING_DECISION = "DRY_RUN_REJECTED_MISSING_DECISION"
DRY_RUN_REJECTED_RELEASE_HOLD_OVERRIDE = "DRY_RUN_REJECTED_RELEASE_HOLD_OVERRIDE"
DRY_RUN_REJECTED_MISSING_EVIDENCE = "DRY_RUN_REJECTED_MISSING_EVIDENCE"
DRY_RUN_REJECTED_CONFLICTING_CONFIRMATIONS = "DRY_RUN_REJECTED_CONFLICTING_CONFIRMATIONS"
DRY_RUN_REJECTED_UNSAFE_ACTION_REQUEST = "DRY_RUN_REJECTED_UNSAFE_ACTION_REQUEST"
DRY_RUN_NEEDS_MORE_REVIEW = "DRY_RUN_NEEDS_MORE_REVIEW"
DRY_RUN_REJECTED = "DRY_RUN_REJECTED"


@dataclass(frozen=True)
class FormValidation:
    """Validation result for a single form."""
    completed_form_id: str
    source_form_id: str
    path: str
    simulation_category: str
    outcome: str
    reason: str
    action_authorized: bool
    no_action_performed: bool
    release_hold: str

    def to_dict(self) -> dict:
        return {
            "completed_form_id": self.completed_form_id,
            "source_form_id": self.source_form_id,
            "path": self.path,
            "simulation_category": self.simulation_category,
            "outcome": self.outcome,
            "reason": self.reason,
            "action_authorized": self.action_authorized,
            "no_action_performed": self.no_action_performed,
            "release_hold": self.release_hold,
        }


@dataclass(frozen=True)
class DryRunValidation:
    """Full dry-run validation result."""
    results: list[FormValidation]
    total_count: int
    outcome_counts: dict[str, int]
    accepted_count: int
    rejected_count: int
    needs_review_count: int
    release_hold: str
    action_authorized: bool = False
    no_action_performed: bool = True

    def to_dict(self) -> dict:
        return {
            "results": [r.to_dict() for r in self.results],
            "total_count": self.total_count,
            "outcome_counts": dict(sorted(self.outcome_counts.items())),
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "needs_review_count": self.needs_review_count,
            "release_hold": self.release_hold,
            "action_authorized": self.action_authorized,
            "no_action_performed": self.no_action_performed,
        }


def _validate_single(form: dict, release_hold: str) -> FormValidation:
    """Validate a single simulated completed form."""
    fid = form.get("completed_form_id", "unknown")
    sid = form.get("source_form_id", "unknown")
    path = form.get("path", "unknown")
    cat = form.get("simulation_category", "unknown")
    reviewer = form.get("reviewer_name", "")
    decision = form.get("human_decision", "")
    rh = form.get("release_hold", "")
    advisory = form.get("advisory_only", False)
    hrr = form.get("human_review_required", False)
    action_req = form.get("action_requested", False)
    no_action = form.get("no_action_performed", True)
    evidence_status = form.get("evidence_status", "")
    hash_confirmed = form.get("hash_evidence_confirmed", False)
    rollback_confirmed = form.get("rollback_evidence_confirmed", False)
    backup_confirmed = form.get("backup_evidence_confirmed", False)
    mandatory = form.get("mandatory_confirmations_checked", [])
    forbidden = form.get("forbidden_confirmations_checked", [])

    # 1. Missing reviewer
    if not reviewer or reviewer == "PENDING_HUMAN_REVIEWER":
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_REJECTED_MISSING_REVIEWER,
            reason="reviewer_name is empty or placeholder",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 2. Missing decision
    if not decision:
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_REJECTED_MISSING_DECISION,
            reason="human_decision is empty",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 3. Forbidden decision
    if decision in FORBIDDEN_DECISIONS:
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_REJECTED_FORBIDDEN_DECISION,
            reason=f"forbidden decision={decision!r}",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 4. Release hold override
    if rh != release_hold:
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_REJECTED_RELEASE_HOLD_OVERRIDE,
            reason=f"release_hold={rh!r} != {release_hold!r}",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 5. Advisory only
    if not advisory:
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_REJECTED,
            reason="advisory_only is not true",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 6. Human review required
    if not hrr:
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_REJECTED,
            reason="human_review_required is not true",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 7. Action requested
    if action_req:
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_REJECTED_UNSAFE_ACTION_REQUEST,
            reason="action_requested is true",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 8. no_action_performed must be true
    if not no_action:
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_REJECTED,
            reason="no_action_performed is not true",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 9. Conflicting confirmations
    forbidden_set = set(forbidden)
    mandatory_set = set(mandatory)
    conflict = forbidden_set & mandatory_set
    if conflict:
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_REJECTED_CONFLICTING_CONFIRMATIONS,
            reason=f"conflicting confirmations: {sorted(conflict)}",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 10. REQUEST_MORE_REVIEW
    if decision == "REQUEST_MORE_REVIEW":
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_NEEDS_MORE_REVIEW,
            reason="decision is REQUEST_MORE_REVIEW",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 11. REJECT
    if decision == "REJECT":
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_REJECTED,
            reason="decision is REJECT",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 12. KEEP_FROZEN accepted without full evidence
    if decision == "KEEP_FROZEN":
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_ACCEPTED_PREPARE_ONLY,
            reason="KEEP_FROZEN accepted as prepare-only (no action authorized)",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # 13. Prepare actions require evidence
    if decision in (
        "APPROVE_PREPARE_ARCHIVE_AFTER_BACKUP",
        "APPROVE_PREPARE_DELETE_AFTER_BACKUP",
        "APPROVE_PREPARE_OFFLINE_REWRITE",
    ):
        if evidence_status != "COMPLETE_FOR_HUMAN_REVIEW":
            return FormValidation(
                completed_form_id=fid, source_form_id=sid, path=path,
                simulation_category=cat,
                outcome=DRY_RUN_REJECTED_MISSING_EVIDENCE,
                reason=f"evidence_status={evidence_status!r}, need COMPLETE_FOR_HUMAN_REVIEW",
                action_authorized=False, no_action_performed=True,
                release_hold=rh,
            )
        if not (hash_confirmed and backup_confirmed and rollback_confirmed):
            missing = []
            if not hash_confirmed:
                missing.append("hash")
            if not backup_confirmed:
                missing.append("backup")
            if not rollback_confirmed:
                missing.append("rollback")
            return FormValidation(
                completed_form_id=fid, source_form_id=sid, path=path,
                simulation_category=cat,
                outcome=DRY_RUN_REJECTED_MISSING_EVIDENCE,
                reason=f"missing evidence: {', '.join(missing)}",
                action_authorized=False, no_action_performed=True,
                release_hold=rh,
            )
        return FormValidation(
            completed_form_id=fid, source_form_id=sid, path=path,
            simulation_category=cat,
            outcome=DRY_RUN_ACCEPTED_PREPARE_ONLY,
            reason=f"{decision} accepted as prepare-only (no action authorized)",
            action_authorized=False, no_action_performed=True,
            release_hold=rh,
        )

    # Unknown decision
    return FormValidation(
        completed_form_id=fid, source_form_id=sid, path=path,
        simulation_category=cat,
        outcome=DRY_RUN_REJECTED,
        reason=f"unknown decision={decision!r}",
        action_authorized=False, no_action_performed=True,
        release_hold=rh,
    )


def validate_forms(forms: list[dict], release_hold: str = RELEASE_HOLD_REQUIRED) -> DryRunValidation:
    """Validate all simulated completed forms."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    results = [_validate_single(f, release_hold) for f in forms]

    outcome_counts: dict[str, int] = {}
    for r in results:
        outcome_counts[r.outcome] = outcome_counts.get(r.outcome, 0) + 1

    accepted = sum(1 for r in results if r.outcome == DRY_RUN_ACCEPTED_PREPARE_ONLY)
    rejected = sum(1 for r in results if "REJECTED" in r.outcome)
    needs_review = sum(1 for r in results if r.outcome == DRY_RUN_NEEDS_MORE_REVIEW)

    return DryRunValidation(
        results=results,
        total_count=len(results),
        outcome_counts=outcome_counts,
        accepted_count=accepted,
        rejected_count=rejected,
        needs_review_count=needs_review,
        release_hold=release_hold,
    )


def render_validation_markdown(validation: DryRunValidation) -> str:
    lines = [
        "# Frozen Approval Dry-Run Validation",
        "",
        f"**Total forms validated:** {validation.total_count}",
        f"**Accepted (prepare-only):** {validation.accepted_count}",
        f"**Rejected:** {validation.rejected_count}",
        f"**Needs more review:** {validation.needs_review_count}",
        f"**release_hold:** {validation.release_hold}",
        f"**action_authorized:** {validation.action_authorized}",
        f"**no_action_performed:** {validation.no_action_performed}",
        "",
        "## Outcome Counts",
        "",
    ]
    for outcome, count in sorted(validation.outcome_counts.items()):
        lines.append(f"- **{outcome}:** {count}")

    lines.append("")
    lines.append("## Validation Results")
    lines.append("")
    for r in validation.results:
        status = "ACCEPTED" if r.outcome == DRY_RUN_ACCEPTED_PREPARE_ONLY else "REJECTED" if "REJECTED" in r.outcome else "NEEDS_REVIEW"
        lines.append(f"- **{r.completed_form_id}:** {status} — {r.outcome} — {r.reason}")

    lines.append("")
    lines.append("---")
    lines.append("NO ACTION AUTHORIZED. ALL OUTCOMES ARE PREPARE-ONLY.")
    lines.append("")
    return "\n".join(lines)


def render_manifest(validation: DryRunValidation) -> dict:
    h = hashlib.sha256(
        json.dumps(validation.to_dict(), sort_keys=True, indent=2).encode()
    ).hexdigest()
    return {
        "total_count": validation.total_count,
        "accepted_count": validation.accepted_count,
        "rejected_count": validation.rejected_count,
        "needs_review_count": validation.needs_review_count,
        "outcome_counts": dict(sorted(validation.outcome_counts.items())),
        "release_hold": validation.release_hold,
        "action_authorized": validation.action_authorized,
        "validation_hash": h,
    }
