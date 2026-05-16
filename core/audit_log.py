from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


class AuditLog:
    def __init__(self, *, max_events: int = 5000):
        self.max_events = max(100, int(max_events))
        self._events: list[dict[str, Any]] = []
        self._sequence = 0

    def append_audit_event(
        self,
        *,
        event_type: str,
        severity: str = "INFO",
        payload: Optional[dict[str, Any]] = None,
        symbol: str = "",
        trade_id: Any = None,
        order_id: Any = None,
        timestamp: Optional[Any] = None,
    ) -> dict[str, Any]:
        self._sequence += 1
        event = {
            "event_id": f"AUD-{self._sequence}",
            "event_type": str(event_type or "unknown"),
            "timestamp": _normalize_timestamp(timestamp),
            "symbol": str(symbol or ""),
            "trade_id": trade_id,
            "order_id": order_id,
            "severity": str(severity or "INFO").upper(),
            "payload": dict(payload or {}),
        }
        self._events.append(event)
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events :]
        return dict(event)

    def list_audit_events(self) -> list[dict[str, Any]]:
        return [dict(event) for event in self._events]

    def replay_audit_events(
        self,
        *,
        event_type: Optional[str] = None,
        trade_id: Optional[Any] = None,
        order_id: Optional[Any] = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for event in self._events:
            if event_type not in (None, "") and str(event.get("event_type", "")) != str(event_type):
                continue
            if trade_id not in (None, "") and str(event.get("trade_id", "")) != str(trade_id):
                continue
            if order_id not in (None, "") and str(event.get("order_id", "")) != str(order_id):
                continue
            results.append(dict(event))
        return results


def _normalize_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value not in (None, ""):
        return str(value)
    return datetime.now(timezone.utc).isoformat()
