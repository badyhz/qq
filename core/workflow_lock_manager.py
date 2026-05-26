"""Workflow lock manager for preventing concurrent writes across agents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


class LockError(Exception):
    pass


@dataclass(frozen=True)
class LockInfo:
    component_path: str
    holder_task: str
    holder_agent: str
    acquired_at: str  # ISO timestamp


class WorkflowLockManager:
    def __init__(self) -> None:
        self._locks: Dict[str, LockInfo] = {}  # path -> lock info

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(
        self, component_path: str, task_id: str, agent_id: str = ""
    ) -> LockInfo:
        """Acquire exclusive lock on component.

        Raises LockError if already locked by another task.
        Same task may re-acquire (reentrant).
        """
        existing = self._locks.get(component_path)
        if existing is not None:
            if existing.holder_task == task_id:
                # Reentrant: same task re-acquires -> update timestamp
                info = LockInfo(
                    component_path=component_path,
                    holder_task=task_id,
                    holder_agent=existing.holder_agent or agent_id,
                    acquired_at=datetime.now(timezone.utc).isoformat(),
                )
                self._locks[component_path] = info
                return info
            raise LockError(
                f"Component '{component_path}' is locked by task '{existing.holder_task}'"
            )

        info = LockInfo(
            component_path=component_path,
            holder_task=task_id,
            holder_agent=agent_id,
            acquired_at=datetime.now(timezone.utc).isoformat(),
        )
        self._locks[component_path] = info
        return info

    def release(self, component_path: str, task_id: str) -> None:
        """Release lock. Only holder can release.

        Raises LockError if not holder or not locked.
        """
        existing = self._locks.get(component_path)
        if existing is None:
            raise LockError(f"Component '{component_path}' is not locked")
        if existing.holder_task != task_id:
            raise LockError(
                f"Task '{task_id}' is not the lock holder for '{component_path}' "
                f"(holder: '{existing.holder_task}')"
            )
        del self._locks[component_path]

    def is_locked(self, component_path: str) -> bool:
        """Check if component is locked."""
        return component_path in self._locks

    def get_holder(self, component_path: str) -> Optional[LockInfo]:
        """Get current lock holder."""
        return self._locks.get(component_path)

    def try_acquire(
        self, component_path: str, task_id: str, agent_id: str = ""
    ) -> Optional[LockInfo]:
        """Try to acquire lock. Returns None if locked (no exception)."""
        existing = self._locks.get(component_path)
        if existing is not None:
            if existing.holder_task == task_id:
                return self.acquire(component_path, task_id, agent_id)
            return None
        return self.acquire(component_path, task_id, agent_id)

    def force_release(
        self, component_path: str, admin_task: str = "ADMIN"
    ) -> Optional[LockInfo]:
        """Force release a lock. Returns released lock info."""
        existing = self._locks.pop(component_path, None)
        return existing

    def list_locks(self) -> List[LockInfo]:
        """List all active locks."""
        return list(self._locks.values())

    def summary(self) -> dict:
        """Lock manager stats."""
        locks = self.list_locks()
        agents = {l.holder_agent for l in locks if l.holder_agent}
        return {
            "total_locks": len(locks),
            "unique_agents": len(agents),
            "locked_components": [l.component_path for l in locks],
        }
