from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceItem:
    name: str
    required: bool
    verified: bool


@dataclass(frozen=True)
class HumanReviewEvidenceChecklist:
    gate_id: str
    items: tuple[EvidenceItem, ...]


def build_evidence_item(
    name: str,
    required: bool = True,
    verified: bool = False,
) -> EvidenceItem:
    return EvidenceItem(name=name, required=required, verified=verified)


def build_evidence_checklist(
    gate_id: str,
    items: tuple[EvidenceItem, ...] = (),
) -> HumanReviewEvidenceChecklist:
    return HumanReviewEvidenceChecklist(
        gate_id=gate_id,
        items=tuple(items),
    )


def all_required_verified(checklist: HumanReviewEvidenceChecklist) -> bool:
    return all(
        item.verified for item in checklist.items if item.required
    )
