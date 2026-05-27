from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumRiskImportBoundary:
    """T1213 - frozen dataclass for import boundary policy."""

    module_name: str
    allowed_imports: tuple[str, ...]
    forbidden_imports: tuple[str, ...]
    requires_abstraction: bool
