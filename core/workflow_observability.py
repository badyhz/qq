from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import time


class EventType(Enum):
    TASK_SUBMITTED = "task_submitted"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_BLOCKED = "task_blocked"
    BUDGET_EXCEEDED = "budget_exceeded"
    CIRCUIT_OPENED = "circuit_opened"
    SAFETY_VIOLATION = "safety_violation"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"


@dataclass
class Event:
    event_type: EventType
    task_id: str
    adapter_id: str
    timestamp: float
    metadata: dict = field(default_factory=dict)


class WorkflowObservability:
    def __init__(self):
        self._events: list[Event] = []

    def emit(self, event_type: EventType, task_id: str = "",
             adapter_id: str = "", **metadata) -> Event:
        event = Event(
            event_type=event_type,
            task_id=task_id,
            adapter_id=adapter_id,
            timestamp=time.time(),
            metadata=metadata,
        )
        self._events.append(event)
        return event

    def query(self, event_type: Optional[EventType] = None,
              task_id: Optional[str] = None) -> list[Event]:
        results = self._events
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if task_id is not None:
            results = [e for e in results if e.task_id == task_id]
        return results

    def task_events(self, task_id: str) -> list[Event]:
        return [e for e in self._events if e.task_id == task_id]

    def timeline(self, task_id: str) -> list[dict]:
        events = self.task_events(task_id)
        return [
            {
                "event": e.event_type.value,
                "timestamp": e.timestamp,
                "task_id": e.task_id,
                "adapter_id": e.adapter_id,
                "metadata": e.metadata,
            }
            for e in events
        ]

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for e in self._events:
            key = e.event_type.value
            counts[key] = counts.get(key, 0) + 1
        return {"total": len(self._events), "counts": counts}

    def duration_ms(self, task_id: str) -> Optional[float]:
        events = self.task_events(task_id)
        started = [e for e in events if e.event_type in (EventType.TASK_STARTED, EventType.TASK_SUBMITTED)]
        ended = [e for e in events if e.event_type in (EventType.TASK_COMPLETED, EventType.TASK_FAILED)]
        if not started or not ended:
            return None
        return (ended[0].timestamp - started[0].timestamp) * 1000

    def failure_rate(self) -> float:
        completed = sum(1 for e in self._events if e.event_type == EventType.TASK_COMPLETED)
        failed = sum(1 for e in self._events if e.event_type == EventType.TASK_FAILED)
        total = completed + failed
        if total == 0:
            return 0.0
        return failed / total

    def clear(self) -> None:
        self._events.clear()
