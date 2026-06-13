"""Alert dedup store. Persists dedup state across runs."""
from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DedupEntry:
    dedup_key: str
    first_seen: str
    last_seen: str
    count: int
    last_severity: str

    def to_dict(self) -> dict:
        return {
            "dedup_key": self.dedup_key,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "count": self.count,
            "last_severity": self.last_severity,
        }


class DedupStore:
    """Persistent dedup store for alert events."""

    def __init__(self, store_path: pathlib.Path):
        self._path = store_path
        self._entries: dict[str, DedupEntry] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for item in data:
                    self._entries[item["dedup_key"]] = DedupEntry(**item)
            except (json.JSONDecodeError, KeyError):
                pass

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([e.to_dict() for e in self._entries.values()], indent=2),
            encoding="utf-8",
        )

    def is_duplicate(self, dedup_key: str) -> bool:
        return dedup_key in self._entries

    def record(self, dedup_key: str, severity: str) -> bool:
        """Record an alert. Returns True if it's a new (non-duplicate) alert."""
        now = datetime.now(timezone.utc).isoformat()
        if dedup_key in self._entries:
            existing = self._entries[dedup_key]
            self._entries[dedup_key] = DedupEntry(
                dedup_key=dedup_key,
                first_seen=existing.first_seen,
                last_seen=now,
                count=existing.count + 1,
                last_severity=severity,
            )
            return False
        else:
            self._entries[dedup_key] = DedupEntry(
                dedup_key=dedup_key,
                first_seen=now,
                last_seen=now,
                count=1,
                last_severity=severity,
            )
            return True

    def suppress_count(self) -> int:
        return sum(e.count - 1 for e in self._entries.values() if e.count > 1)

    def total_unique(self) -> int:
        return len(self._entries)

    def total_records(self) -> int:
        return sum(e.count for e in self._entries.values())
