from __future__ import annotations


class UntrackedAllowedAction:
    """Enum-like frozen class for allowed actions on untracked files."""

    INSPECT = "INSPECT"
    CLASSIFY = "CLASSIFY"
    LOG = "LOG"
    REPORT = "REPORT"

    ALL_ACTIONS = (INSPECT, CLASSIFY, LOG, REPORT)

    def __init__(self, value: str) -> None:
        if value not in self.ALL_ACTIONS:
            raise ValueError(
                f"Invalid allowed action: {value!r}. "
                f"Must be one of: {', '.join(self.ALL_ACTIONS)}"
            )
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UntrackedAllowedAction):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"UntrackedAllowedAction({self._value!r})"

    def __str__(self) -> str:
        return self._value


def validate_action(action: str) -> bool:
    """Return True if action is a valid UntrackedAllowedAction value."""
    return action in UntrackedAllowedAction.ALL_ACTIONS
