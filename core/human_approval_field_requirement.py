"""T1332 - Human approval field requirement specification."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanApprovalFieldRequirement:
    """Declares a single field that an evidence pack must satisfy."""

    field_id: str
    field_name: str
    field_type: str
    required: bool
    validation_rule: str

    def to_dict(self) -> dict[str, object]:
        return {
            "field_id": self.field_id,
            "field_name": self.field_name,
            "field_type": self.field_type,
            "required": self.required,
            "validation_rule": self.validation_rule,
        }

    def is_satisfied_by(self, value_type: str) -> bool:
        """Check whether a provided value type matches the requirement."""
        return value_type == self.field_type
