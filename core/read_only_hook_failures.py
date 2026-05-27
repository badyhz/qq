"""Read-only hook failures — pure frozen dataclasses, no I/O."""
from __future__ import annotations

from dataclasses import dataclass

FAILURE_CATEGORIES = [
    "PERMISSION_DENIED",
    "INVARIANT_VIOLATION",
    "SANITIZATION_FAILURE",
    "TIMEOUT",
    "UNKNOWN",
]

_RECOVERABLE = {
    "PERMISSION_DENIED": False,
    "INVARIANT_VIOLATION": False,
    "SANITIZATION_FAILURE": True,
    "TIMEOUT": True,
    "UNKNOWN": False,
}


@dataclass(frozen=True)
class HookFailure:
    failure_id: str
    category: str
    task_id: str
    message: str
    recoverable: bool


def classify_failure(category: str, message: str, task_id: str = "", failure_id: str = "") -> HookFailure:
    if category not in FAILURE_CATEGORIES:
        category = "UNKNOWN"
    if not failure_id:
        failure_id = f"fail_{category.lower()}"
    if not task_id:
        task_id = "unspecified"
    return HookFailure(
        failure_id=failure_id,
        category=category,
        task_id=task_id,
        message=message,
        recoverable=_RECOVERABLE.get(category, False),
    )


def hook_failure_to_dict(hf: HookFailure) -> dict:
    return {
        "failure_id": hf.failure_id,
        "category": hf.category,
        "task_id": hf.task_id,
        "message": hf.message,
        "recoverable": hf.recoverable,
    }
