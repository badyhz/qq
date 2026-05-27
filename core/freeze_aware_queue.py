"""T1111 - Freeze-Aware Queue Model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreezeAwareQueue:
    """Immutable queue snapshot.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    queue_id: str
    tasks: tuple[str, ...]
    frozen_files: tuple[str, ...]
    release_hold: bool
