from __future__ import annotations

from typing import Any

ACTION_CONTINUE = "CONTINUE"
ACTION_SKIP = "SKIP"
ACTION_RETRY = "RETRY"
ACTION_HALT = "HALT"


class FailurePolicy:
    """Minimal runtime-loop failure policy for live runner skeleton."""

    def decide_from_exception(self, exc: Exception) -> str:
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return ACTION_RETRY
        return ACTION_HALT

    def decide_from_runtime_status(self, runtime_status: dict[str, Any]) -> str:
        level = str(runtime_status.get("overall_status", "OK")).strip().upper()
        if level == "ERROR":
            return ACTION_HALT
        return ACTION_CONTINUE

    def decide_from_circuit_breaker(self, can_open_result: dict[str, Any]) -> str:
        if bool(can_open_result.get("can_open", True)):
            return ACTION_CONTINUE
        return ACTION_SKIP

    def decide_from_preflight(self, preflight_report: dict[str, Any]) -> str:
        if bool(preflight_report.get("ok", False)):
            return ACTION_CONTINUE
        return ACTION_HALT


def build_loop_result(action: str, reasons: list[str], loop_snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": action,
        "reasons": reasons,
        "loop_snapshot": loop_snapshot,
    }
