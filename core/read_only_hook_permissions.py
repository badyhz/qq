"""Read-only hook permissions — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass

VALID_PERMISSIONS = frozenset({"read", "query", "inspect", "validate", "report"})
DENIED_PERMISSIONS = frozenset({"write", "execute", "submit", "trade", "delete", "mutate"})


@dataclass(frozen=True)
class ReadOnlyPermission:
    permission_id: str
    name: str
    granted: bool
    denial_reason: str


def check_permission(name: str) -> ReadOnlyPermission:
    if name in VALID_PERMISSIONS:
        return ReadOnlyPermission(
            permission_id=f"perm_{name}",
            name=name,
            granted=True,
            denial_reason="",
        )
    if name in DENIED_PERMISSIONS:
        return ReadOnlyPermission(
            permission_id=f"perm_{name}",
            name=name,
            granted=False,
            denial_reason=f"Permission {name!r} is denied for read-only hooks",
        )
    return ReadOnlyPermission(
        permission_id=f"perm_{name}",
        name=name,
        granted=False,
        denial_reason=f"Unknown permission: {name!r}",
    )


def classify_denied_operation(name: str) -> str:
    write_ops = {"write", "mutate"}
    execute_ops = {"execute", "submit"}
    trade_ops = {"trade"}
    if name in write_ops:
        return "WRITE"
    if name in execute_ops:
        return "EXECUTE"
    if name in trade_ops:
        return "TRADE"
    return "UNKNOWN"


def permission_to_dict(perm: ReadOnlyPermission) -> dict:
    return {
        "permission_id": perm.permission_id,
        "name": perm.name,
        "granted": perm.granted,
        "denial_reason": perm.denial_reason,
    }
