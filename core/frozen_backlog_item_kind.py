"""T1302 - Frozen Backlog Item Kind."""
from __future__ import annotations

from dataclasses import dataclass


HIGH_RISK_FROZEN = "HIGH_RISK_FROZEN"
MEDIUM_OPERATIONAL = "MEDIUM_OPERATIONAL"
MEDIUM_VERIFICATION = "MEDIUM_VERIFICATION"

ALL_KINDS: tuple[str, ...] = (
    HIGH_RISK_FROZEN,
    MEDIUM_OPERATIONAL,
    MEDIUM_VERIFICATION,
)


@dataclass(frozen=True)
class FrozenBacklogItemKind:
    """Immutable backlog item kind.

    Pure deterministic. No I/O. No timestamps. No network.
    """

    kind: str

    def __post_init__(self) -> None:
        if self.kind not in ALL_KINDS:
            raise ValueError(
                f"Invalid kind {self.kind!r}; must be one of {ALL_KINDS}"
            )


def build_kind(kind: str) -> FrozenBacklogItemKind:
    """Factory for FrozenBacklogItemKind."""
    return FrozenBacklogItemKind(kind=kind)


def kind_to_dict(k: FrozenBacklogItemKind) -> dict[str, str]:
    """Convert kind to a plain dict."""
    return {"kind": k.kind}
