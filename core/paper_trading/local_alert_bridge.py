"""Local alert bridge — in-memory alert queue for paper trading events."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class Alert:
    level: AlertLevel
    category: str
    message: str
    source: str = ""


class LocalAlertBridge:
    """In-memory alert queue. No network, no persistence."""

    def __init__(self) -> None:
        self._alerts: List[Alert] = []

    def push(self, level: AlertLevel, category: str, message: str, source: str = "") -> None:
        self._alerts.append(Alert(level=level, category=category, message=message, source=source))

    def info(self, category: str, message: str, source: str = "") -> None:
        self.push(AlertLevel.INFO, category, message, source)

    def warning(self, category: str, message: str, source: str = "") -> None:
        self.push(AlertLevel.WARNING, category, message, source)

    def critical(self, category: str, message: str, source: str = "") -> None:
        self.push(AlertLevel.CRITICAL, category, message, source)

    def drain(self) -> List[Alert]:
        """Return all alerts and clear the queue."""
        alerts = list(self._alerts)
        self._alerts.clear()
        return alerts

    def peek(self) -> List[Alert]:
        """Return all alerts without clearing."""
        return list(self._alerts)

    @property
    def count(self) -> int:
        return len(self._alerts)

    def has_critical(self) -> bool:
        return any(a.level == AlertLevel.CRITICAL for a in self._alerts)
