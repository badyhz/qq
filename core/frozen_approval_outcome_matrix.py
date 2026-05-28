"""T16501 — Frozen Approval Outcome Matrix.

Pure deterministic. No I/O. No network.
Builds outcome matrix from dry-run validation results.
No actual approval granted. No actual action performed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

RELEASE_HOLD_REQUIRED = "HOLD"

FORBIDDEN_NEXT_ACTIONS = (
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
    "SUBMIT_ORDER",
    "CANCEL_ORDER",
    "FLATTEN_POSITION",
)

ALLOWED_NEXT_STEPS = {
    "DRY_RUN_ACCEPTED_PREPARE_ONLY": "Human may review; no action authorized.",
    "DRY_RUN_REJECTED_FORBIDDEN_DECISION": "Form rejected. Forbidden decision detected.",
    "DRY_RUN_REJECTED_MISSING_REVIEWER": "Form rejected. Reviewer name missing.",
    "DRY_RUN_REJECTED_MISSING_DECISION": "Form rejected. Decision missing.",
    "DRY_RUN_REJECTED_RELEASE_HOLD_OVERRIDE": "Form rejected. release_hold override detected.",
    "DRY_RUN_REJECTED_MISSING_EVIDENCE": "Form rejected. Evidence incomplete.",
    "DRY_RUN_REJECTED_CONFLICTING_CONFIRMATIONS": "Form rejected. Conflicting confirmations.",
    "DRY_RUN_REJECTED_UNSAFE_ACTION_REQUEST": "Form rejected. Unsafe auto action requested.",
    "DRY_RUN_NEEDS_MORE_REVIEW": "Form needs additional human review before disposition.",
    "DRY_RUN_REJECTED": "Form rejected. See reason.",
}


@dataclass(frozen=True)
class OutcomeEntry:
    """Single outcome matrix entry."""
    outcome: str
    count: int
    affected_paths: list[str]
    example_form_ids: list[str]
    allowed_next_manual_step: str
    forbidden_next_actions: list[str]
    requires_more_evidence: bool
    requires_human_review: bool
    action_authorized: bool = False
    no_action_performed: bool = True
    release_hold: str = "HOLD"

    def to_dict(self) -> dict:
        return {
            "outcome": self.outcome,
            "count": self.count,
            "affected_paths": sorted(self.affected_paths),
            "example_form_ids": sorted(self.example_form_ids),
            "allowed_next_manual_step": self.allowed_next_manual_step,
            "forbidden_next_actions": list(self.forbidden_next_actions),
            "requires_more_evidence": self.requires_more_evidence,
            "requires_human_review": self.requires_human_review,
            "action_authorized": self.action_authorized,
            "no_action_performed": self.no_action_performed,
            "release_hold": self.release_hold,
        }


@dataclass(frozen=True)
class OutcomeMatrix:
    """Full outcome matrix."""
    entries: list[OutcomeEntry]
    total_forms: int
    total_outcomes: int
    release_hold: str
    action_authorized: bool = False
    no_action_performed: bool = True

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total_forms": self.total_forms,
            "total_outcomes": self.total_outcomes,
            "release_hold": self.release_hold,
            "action_authorized": self.action_authorized,
            "no_action_performed": self.no_action_performed,
        }


def build_outcome_matrix(validation_results: list[dict], release_hold: str = RELEASE_HOLD_REQUIRED) -> OutcomeMatrix:
    """Build outcome matrix from dry-run validation results."""
    if release_hold != RELEASE_HOLD_REQUIRED:
        raise ValueError(f"release_hold={release_hold!r} != HOLD")

    # Group by outcome
    grouped: dict[str, list[dict]] = {}
    for r in validation_results:
        outcome = r.get("outcome", "UNKNOWN")
        grouped.setdefault(outcome, []).append(r)

    entries = []
    for outcome, forms in sorted(grouped.items()):
        paths = list(set(f.get("path", "") for f in forms))
        form_ids = list(set(f.get("completed_form_id", "") for f in forms))[:5]
        needs_evidence = outcome in (
            "DRY_RUN_REJECTED_MISSING_EVIDENCE",
            "DRY_RUN_REJECTED_CONFLICTING_CONFIRMATIONS",
        )
        needs_review = outcome in (
            "DRY_RUN_NEEDS_MORE_REVIEW",
            "DRY_RUN_REJECTED_MISSING_EVIDENCE",
        )
        entries.append(OutcomeEntry(
            outcome=outcome,
            count=len(forms),
            affected_paths=sorted(paths),
            example_form_ids=sorted(form_ids),
            allowed_next_manual_step=ALLOWED_NEXT_STEPS.get(outcome, "Unknown"),
            forbidden_next_actions=list(FORBIDDEN_NEXT_ACTIONS),
            requires_more_evidence=needs_evidence,
            requires_human_review=needs_review,
        ))

    return OutcomeMatrix(
        entries=entries,
        total_forms=len(validation_results),
        total_outcomes=len(entries),
        release_hold=release_hold,
    )


def render_matrix_markdown(matrix: OutcomeMatrix) -> str:
    lines = [
        "# Frozen Approval Outcome Matrix",
        "",
        f"**Total forms:** {matrix.total_forms}",
        f"**Total outcome categories:** {matrix.total_outcomes}",
        f"**release_hold:** {matrix.release_hold}",
        f"**action_authorized:** {matrix.action_authorized}",
        f"**no_action_performed:** {matrix.no_action_performed}",
        "",
        "## Outcome Entries",
        "",
    ]
    for e in matrix.entries:
        lines.append(f"### {e.outcome}")
        lines.append(f"- **Count:** {e.count}")
        lines.append(f"- **Affected paths:** {len(e.affected_paths)}")
        lines.append(f"- **Example forms:** {', '.join(e.example_form_ids[:3])}")
        lines.append(f"- **Allowed next step:** {e.allowed_next_manual_step}")
        lines.append(f"- **Requires more evidence:** {e.requires_more_evidence}")
        lines.append(f"- **Requires human review:** {e.requires_human_review}")
        lines.append(f"- **Action authorized:** {e.action_authorized}")
        lines.append(f"- **Forbidden next actions:** {len(e.forbidden_next_actions)} items")
        lines.append("")

    lines.append("## Forbidden Next Actions (all outcomes)")
    lines.append("")
    for action in FORBIDDEN_NEXT_ACTIONS:
        lines.append(f"- {action}")

    lines.append("")
    lines.append("---")
    lines.append("NO ACTION AUTHORIZED. ALL OUTCOMES ARE PREPARE-ONLY OR REJECTED.")
    lines.append("")
    return "\n".join(lines)


def render_manifest(matrix: OutcomeMatrix) -> dict:
    h = hashlib.sha256(
        json.dumps(matrix.to_dict(), sort_keys=True, indent=2).encode()
    ).hexdigest()
    return {
        "total_forms": matrix.total_forms,
        "total_outcomes": matrix.total_outcomes,
        "release_hold": matrix.release_hold,
        "action_authorized": matrix.action_authorized,
        "matrix_hash": h,
    }
