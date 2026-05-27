"""T1324 — Verification script mocked dependency model."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationScriptMockedDependency:
    """Immutable specification for a mocked dependency in a verification script."""

    dependency_id: str
    original_module: str
    mock_strategy: str
    required: bool

    def is_patch(self) -> bool:
        """Pure: return True if strategy is unittest.mock.patch."""
        return self.mock_strategy == "patch"

    def is_fixture(self) -> bool:
        """Pure: return True if strategy is pytest fixture."""
        return self.mock_strategy == "fixture"

    def is_standalone(self) -> bool:
        """Pure: return True if strategy is standalone mock object."""
        return self.mock_strategy == "standalone"

    def is_dependency_injection(self) -> bool:
        """Pure: return True if strategy is dependency injection."""
        return self.mock_strategy == "injection"

    def summary(self) -> dict[str, str | bool]:
        """Pure: return summary dict."""
        return {
            "dependency_id": self.dependency_id,
            "original_module": self.original_module,
            "mock_strategy": self.mock_strategy,
            "required": self.required,
        }
