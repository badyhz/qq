from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImplementationBoundaryContract:
    contract_id: str
    allowed_scope: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    required_evidence: tuple[str, ...]
    human_approval_required: bool
    release_hold: str

    def __post_init__(self) -> None:
        if self.release_hold != "HOLD":
            raise ValueError(f"release_hold must be HOLD, got {self.release_hold}")

    def is_path_forbidden(self, path: str) -> bool:
        return path in self.forbidden_paths

    def is_in_scope(self, path: str) -> bool:
        return path in self.allowed_scope
