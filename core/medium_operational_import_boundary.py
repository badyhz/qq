"""T1314 — Medium operational import boundary model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumOperationalImportBoundary:
    """Defines allowed and forbidden Python imports for medium-risk scripts."""

    boundary_id: str
    allowed_imports: tuple[str, ...]
    forbidden_imports: tuple[str, ...]

    def is_import_allowed(self, module_name: str) -> bool:
        for forbidden in self.forbidden_imports:
            if module_name == forbidden or module_name.startswith(forbidden + "."):
                return False
        if self.allowed_imports:
            return any(
                module_name == a or module_name.startswith(a + ".")
                for a in self.allowed_imports
            )
        return True

    def is_import_forbidden(self, module_name: str) -> bool:
        return any(
            module_name == f or module_name.startswith(f + ".")
            for f in self.forbidden_imports
        )

    def allowed_count(self) -> int:
        return len(self.allowed_imports)

    def forbidden_count(self) -> int:
        return len(self.forbidden_imports)

    def allowed_set(self) -> frozenset[str]:
        return frozenset(self.allowed_imports)

    def forbidden_set(self) -> frozenset[str]:
        return frozenset(self.forbidden_imports)
