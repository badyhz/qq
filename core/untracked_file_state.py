from __future__ import annotations


class UntrackedFileState:
    """Enum-like frozen class for untracked file states."""

    NEW = "NEW"
    STALE = "STALE"
    FROZEN = "FROZEN"
    DUPLICATE = "DUPLICATE"
    ORPHAN = "ORPHAN"
    QUARANTINED = "QUARANTINED"

    ALL_STATES = (NEW, STALE, FROZEN, DUPLICATE, ORPHAN, QUARANTINED)

    def __init__(self, value: str) -> None:
        if value not in self.ALL_STATES:
            raise ValueError(
                f"Invalid state: {value!r}. "
                f"Must be one of: {', '.join(self.ALL_STATES)}"
            )
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UntrackedFileState):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"UntrackedFileState({self._value!r})"

    def __str__(self) -> str:
        return self._value


def validate_state(state: str) -> bool:
    """Return True if state is a valid UntrackedFileState value."""
    return state in UntrackedFileState.ALL_STATES
