"""T1334 - Human approval timestamp model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanApprovalTimestamp:
    """Immutable timestamp record attached to approval evidence."""

    timestamp_id: str
    iso_format: str
    timezone: str
    precision: str

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp_id": self.timestamp_id,
            "iso_format": self.iso_format,
            "timezone": self.timezone,
            "precision": self.precision,
        }

    def is_utc(self) -> bool:
        return self.timezone.upper() in ("UTC", "+00:00", "Z")
