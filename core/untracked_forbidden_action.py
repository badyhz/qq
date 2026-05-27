from __future__ import annotations


class UntrackedForbiddenAction:
    """Enum-like frozen class for forbidden actions on untracked files."""

    AUTO_COMMIT = "AUTO_COMMIT"
    AUTO_WIRE = "AUTO_WIRE"
    AUTO_RUN = "AUTO_RUN"
    DELETE = "DELETE"
    MODIFY = "MODIFY"

    ALL_ACTIONS = (AUTO_COMMIT, AUTO_WIRE, AUTO_RUN, DELETE, MODIFY)

    def __init__(self, value: str) -> None:
        if value not in self.ALL_ACTIONS:
            raise ValueError(
                f"Invalid forbidden action: {value!r}. "
                f"Must be one of: {', '.join(self.ALL_ACTIONS)}"
            )
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UntrackedForbiddenAction):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"UntrackedForbiddenAction({self._value!r})"

    def __str__(self) -> str:
        return self._value


def validate_action(action: str) -> bool:
    """Return True if action is a valid UntrackedForbiddenAction value."""
    return action in UntrackedForbiddenAction.ALL_ACTIONS
