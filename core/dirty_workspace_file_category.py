from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DirtyWorkspaceFileCategory:
    A_ROUTE: str = "A_ROUTE"
    B_RUNTIME_LIVE: str = "B_RUNTIME_LIVE"
    C_DOCS_READINESS: str = "C_DOCS_READINESS"
    D_TESTS: str = "D_TESTS"
    E_SCRIPTS: str = "E_SCRIPTS"
    F_SAFE_UNRELATED: str = "F_SAFE_UNRELATED"
    G_HUMAN_DECISION: str = "G_HUMAN_DECISION"

    ALL_VALUES: tuple[str, ...] = (
        "A_ROUTE",
        "B_RUNTIME_LIVE",
        "C_DOCS_READINESS",
        "D_TESTS",
        "E_SCRIPTS",
        "F_SAFE_UNRELATED",
        "G_HUMAN_DECISION",
    )


def validate_category(value: str) -> bool:
    return value in DirtyWorkspaceFileCategory.ALL_VALUES
