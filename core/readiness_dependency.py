from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DependencyType(Enum):
    BLOCKS = "BLOCKS"
    REQUIRES = "REQUIRES"
    ENABLES = "ENABLES"


@dataclass(frozen=True)
class ReadinessDependency:
    """Frozen dependency edge. No I/O, no timestamps."""

    source_task: str
    target_task: str
    dependency_type: DependencyType
    resolved: bool
