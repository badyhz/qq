"""T1612 - FrozenDiffChange frozen dataclass.

Pure frozen dataclass for a single field-level diff change.
No I/O. No timestamps. No network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FrozenDiffChange:
    """Immutable representation of a single field change in a frozen file entry.

    Pure frozen. No I/O. No timestamps. No network.
    """

    file_path: str
    field_name: str
    old_value: Any
    new_value: Any
