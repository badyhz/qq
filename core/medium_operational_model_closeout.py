"""T1320 — Medium operational model closeout."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumOperationalModelCloseout:
    """Closeout record for medium-operational review module batch."""

    closeout_id: str
    task_range: str
    models_created: tuple[str, ...]
    verdict: str

    def model_count(self) -> int:
        return len(self.models_created)

    def model_set(self) -> frozenset[str]:
        return frozenset(self.models_created)

    def is_complete(self) -> bool:
        return self.verdict == "COMPLETE"

    def is_hold(self) -> bool:
        return self.verdict == "HOLD"

    def is_failed(self) -> bool:
        return self.verdict == "FAILED"

    def contains_model(self, model_name: str) -> bool:
        return model_name in self.models_created
