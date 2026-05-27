from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoSubmitReleaseGate:
    gate_id: str
    invariants: tuple[str, ...]
    denied_operations: tuple[str, ...]
    verdict: str
