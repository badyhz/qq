from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UntrackedFreezeLedger:
    """Frozen ledger of untracked files with freeze policy enforcement."""

    ledger_id: str
    entries: tuple  # tuple of UntrackedFileLedgerRecord
    frozen_files: tuple  # tuple of file paths (str)
    release_hold: bool

    def is_empty(self) -> bool:
        return len(self.entries) == 0

    def frozen_count(self) -> int:
        return len(self.frozen_files)

    def has_release_hold(self) -> bool:
        return self.release_hold

    def ledger_to_dict(self) -> dict:
        return {
            "ledger_id": self.ledger_id,
            "entries": tuple(e for e in self.entries),
            "frozen_files": tuple(self.frozen_files),
            "release_hold": self.release_hold,
        }
