from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChecklistItem:
    """Single checklist item."""

    name: str
    required: bool
    verified: bool


@dataclass(frozen=True)
class MediumRiskPromotionChecklist:
    """T1218 - frozen dataclass for promotion checklist."""

    items: tuple[ChecklistItem, ...]


def build_default_checklist() -> MediumRiskPromotionChecklist:
    """Build the default promotion checklist with all items unverified."""
    return MediumRiskPromotionChecklist(
        items=tuple(
            ChecklistItem(name=name, required=True, verified=False)
            for name in (
                "dry_run_verified",
                "imports_clean",
                "no_secrets",
                "no_live_paths",
                "human_approved",
            )
        )
    )
