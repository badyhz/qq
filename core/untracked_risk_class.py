from __future__ import annotations


class UntrackedRiskClass:
    """Enum-like frozen class for untracked file risk classes."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    ALL_CLASSES = (HIGH, MEDIUM, LOW)

    _DEFAULT_ACTIONS = {
        HIGH: "BLOCK",
        MEDIUM: "HOLD",
        LOW: "LOG",
    }

    def __init__(self, value: str) -> None:
        if value not in self.ALL_CLASSES:
            raise ValueError(
                f"Invalid risk class: {value!r}. "
                f"Must be one of: {', '.join(self.ALL_CLASSES)}"
            )
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UntrackedRiskClass):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"UntrackedRiskClass({self._value!r})"

    def __str__(self) -> str:
        return self._value


def risk_class_to_default_action(risk_class: str) -> str:
    """Return the default action for a given risk class."""
    actions = {
        "HIGH": "BLOCK",
        "MEDIUM": "HOLD",
        "LOW": "LOG",
    }
    if risk_class not in actions:
        raise ValueError(
            f"Invalid risk class: {risk_class!r}. "
            f"Must be one of: {', '.join(actions.keys())}"
        )
    return actions[risk_class]
