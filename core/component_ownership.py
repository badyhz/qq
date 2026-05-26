"""Component ownership registry to prevent concurrent overwrites."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


class ConflictError(Exception):
    """Raised when a component is already owned by a different task."""


@dataclass
class OwnershipEntry:
    component_path: str
    owner_task: str
    owner_agent: str
    registered_at: str
    permission: str  # "exclusive" | "shared"


class ComponentOwnershipRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, OwnershipEntry] = {}

    def register(
        self,
        component_path: str,
        owner_task: str,
        owner_agent: str = "",
        permission: str = "exclusive",
    ) -> OwnershipEntry:
        """Register ownership. Raises ConflictError if path already owned by different task."""
        existing = self._entries.get(component_path)
        if existing is not None:
            if existing.owner_task != owner_task:
                raise ConflictError(
                    f"Component '{component_path}' is owned by task '{existing.owner_task}', "
                    f"cannot register to task '{owner_task}'"
                )
            # Same task re-registering -- update agent/permission
            existing.owner_agent = owner_agent or existing.owner_agent
            existing.permission = permission
            return existing

        entry = OwnershipEntry(
            component_path=component_path,
            owner_task=owner_task,
            owner_agent=owner_agent,
            registered_at=datetime.now(timezone.utc).isoformat(),
            permission=permission,
        )
        self._entries[component_path] = entry
        return entry

    def check(self, component_path: str, requesting_task: str) -> bool:
        """Return True if requesting_task can write to component_path."""
        entry = self._entries.get(component_path)
        if entry is None:
            return True  # unowned, anyone can write
        if entry.owner_task == requesting_task:
            return True
        if entry.permission == "shared":
            return True
        return False

    def get_owner(self, component_path: str) -> OwnershipEntry | None:
        """Get current owner of a component."""
        return self._entries.get(component_path)

    def release(self, component_path: str, releasing_task: str) -> None:
        """Release ownership. Only owner can release."""
        entry = self._entries.get(component_path)
        if entry is None:
            raise ConflictError(f"No ownership entry for '{component_path}'")
        if entry.owner_task != releasing_task:
            raise ConflictError(
                f"Task '{releasing_task}' does not own '{component_path}'"
            )
        del self._entries[component_path]

    def list_owned(self, owner_task: str) -> list[str]:
        """List all components owned by a task."""
        return [
            path
            for path, entry in self._entries.items()
            if entry.owner_task == owner_task
        ]

    def conflicts(self) -> list[dict]:
        """Return list of detected conflicts (multiple owners on same path).

        Since register() rejects duplicates, this currently always returns
        an empty list. It exists for forward-compatibility with
        external/imported registries that might pre-populate entries.
        """
        return []

    def summary(self) -> dict:
        """Return registry stats."""
        tasks: dict[str, int] = {}
        permissions: dict[str, int] = {}
        for entry in self._entries.values():
            tasks[entry.owner_task] = tasks.get(entry.owner_task, 0) + 1
            permissions[entry.permission] = permissions.get(entry.permission, 0) + 1
        return {
            "total_components": len(self._entries),
            "tasks": tasks,
            "permissions": permissions,
        }
