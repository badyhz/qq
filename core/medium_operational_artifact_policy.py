"""T1313 — Medium operational artifact write-path policy model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MediumOperationalArtifactPolicy:
    """Defines allowed and forbidden filesystem write paths."""

    policy_id: str
    allowed_write_paths: tuple[str, ...]
    forbidden_write_paths: tuple[str, ...]

    def is_path_allowed(self, path: str) -> bool:
        for forbidden in self.forbidden_write_paths:
            if path.startswith(forbidden):
                return False
        if self.allowed_write_paths:
            return any(path.startswith(p) for p in self.allowed_write_paths)
        return True

    def is_path_forbidden(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.forbidden_write_paths)

    def allowed_count(self) -> int:
        return len(self.allowed_write_paths)

    def forbidden_count(self) -> int:
        return len(self.forbidden_write_paths)

    def allowed_set(self) -> frozenset[str]:
        return frozenset(self.allowed_write_paths)

    def forbidden_set(self) -> frozenset[str]:
        return frozenset(self.forbidden_write_paths)
