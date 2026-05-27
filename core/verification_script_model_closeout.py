"""T1330 — Verification script model closeout."""
from __future__ import annotations
from dataclasses import dataclass

VALID_CLOSEOUT_VERDICTS = ("pass", "hold", "fail")


@dataclass(frozen=True)
class VerificationScriptModelCloseout:
    """Immutable closeout record for T1321-T1330 model suite."""

    closeout_id: str
    task_range: str
    models_created: tuple[str, ...]
    verdict: str

    def model_count(self) -> int:
        """Pure: return count of models created."""
        return len(self.models_created)

    def has_model(self, model_name: str) -> bool:
        """Pure: check if a model name exists in the created list."""
        return model_name in self.models_created

    def is_pass(self) -> bool:
        """Pure: return True if verdict is pass."""
        return self.verdict == "pass"

    def is_hold(self) -> bool:
        """Pure: return True if verdict is hold."""
        return self.verdict == "hold"

    def is_fail(self) -> bool:
        """Pure: return True if verdict is fail."""
        return self.verdict == "fail"

    def task_range_valid(self) -> bool:
        """Pure: validate task_range format (e.g. 'T1321-T1330')."""
        if "-" not in self.task_range:
            return False
        parts = self.task_range.split("-")
        if len(parts) != 2:
            return False
        return parts[0].startswith("T") and parts[1].startswith("T")

    def summary(self) -> dict[str, str | int | list[str]]:
        """Pure: return summary dict."""
        return {
            "closeout_id": self.closeout_id,
            "task_range": self.task_range,
            "model_count": self.model_count(),
            "verdict": self.verdict,
            "models": list(self.models_created),
        }
