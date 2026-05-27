"""Read-only hook review — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ReviewChecklistItem:
    item_id: str
    description: str
    checked: bool
    notes: str


@dataclass(frozen=True)
class ReviewChecklist:
    checklist_id: str
    items: List[ReviewChecklistItem]
    all_checked: bool
    verdict: str  # "APPROVED", "REJECTED", "PENDING"


VALID_VERDICTS = frozenset({"APPROVED", "REJECTED", "PENDING"})


def build_default_review_checklist() -> ReviewChecklist:
    items = [
        ReviewChecklistItem("rc_01", "All dataclasses are frozen", False, ""),
        ReviewChecklistItem("rc_02", "No I/O operations in any module", False, ""),
        ReviewChecklistItem("rc_03", "No network calls", False, ""),
        ReviewChecklistItem("rc_04", "No timestamp generation", False, ""),
        ReviewChecklistItem("rc_05", "No random number generation", False, ""),
        ReviewChecklistItem("rc_06", "Secrets are redacted in sanitizer", False, ""),
        ReviewChecklistItem("rc_07", "Permission checks cover all denied ops", False, ""),
        ReviewChecklistItem("rc_08", "Invariant checks cover all five invariants", False, ""),
        ReviewChecklistItem("rc_09", "All serializers produce plain dicts", False, ""),
        ReviewChecklistItem("rc_10", "Side effects list must be empty for read-only", False, ""),
    ]
    return ReviewChecklist(
        checklist_id="review_default",
        items=items,
        all_checked=False,
        verdict="PENDING",
    )


def review_checklist_item_to_dict(item: ReviewChecklistItem) -> dict:
    return {
        "item_id": item.item_id,
        "description": item.description,
        "checked": item.checked,
        "notes": item.notes,
    }


def review_checklist_to_dict(rc: ReviewChecklist) -> dict:
    return {
        "checklist_id": rc.checklist_id,
        "items": [review_checklist_item_to_dict(i) for i in rc.items],
        "all_checked": rc.all_checked,
        "verdict": rc.verdict,
    }
