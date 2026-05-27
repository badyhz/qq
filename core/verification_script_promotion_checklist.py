"""T1328 — Verification script promotion checklist model."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationScriptPromotionChecklist:
    """Immutable checklist gating script promotion to higher environments."""

    checklist_id: str
    items: tuple[str, ...]
    all_required: bool
    completed_count: int

    def total_items(self) -> int:
        """Pure: return total number of items."""
        return len(self.items)

    def remaining(self) -> int:
        """Pure: return count of incomplete items."""
        return max(0, self.total_items() - self.completed_count)

    def completion_ratio(self) -> float:
        """Pure: return ratio of completed to total items."""
        total = self.total_items()
        if total == 0:
            return 1.0
        return self.completed_count / total

    def is_complete(self) -> bool:
        """Pure: return True if all items are completed."""
        return self.completed_count >= self.total_items()

    def is_promotable(self) -> bool:
        """Pure: return True if promotion criteria are met."""
        if not self.all_required:
            return self.completed_count > 0
        return self.is_complete()

    def summary(self) -> dict[str, int | float | bool]:
        """Pure: return summary dict."""
        return {
            "checklist_id": self.checklist_id,
            "total_items": self.total_items(),
            "completed_count": self.completed_count,
            "remaining": self.remaining(),
            "completion_ratio": round(self.completion_ratio(), 3),
            "is_promotable": self.is_promotable(),
        }
