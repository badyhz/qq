"""Pure validation for execution guard reports.

No network, no subprocess, no filesystem write, no high-risk imports.
"""
from __future__ import annotations

from typing import Any

# Schema contract — OK reports from build_execution_guard_report + status overlay
_REQUIRED_OK_KEYS = frozenset({
    "status",
    "mode",
    "action",
    "env_overrides",
    "layer0_blocked",
    "layer1_capability",
    "layer2_cli_allow",
    "layer3_env_unlock",
    "layer4_manual_confirm",
    "layer5_symbol_ok",
})

# Schema contract — BLOCKED reports from generate_execution_guard_status_report
_REQUIRED_BLOCKED_KEYS = frozenset({
    "status",
    "reason",
    "action",
    "symbol",
    "env_overrides",
})

_VALID_STATUSES = frozenset({"OK", "BLOCKED"})


def assert_guard_report_keys(report: dict) -> None:
    """Raise ValueError if report is missing required keys for its status."""
    if not isinstance(report, dict):
        raise ValueError(f"report must be dict, got {type(report).__name__}")

    status = report.get("status")
    if status not in _VALID_STATUSES:
        raise ValueError(
            f"invalid status: {status!r}, expected one of {sorted(_VALID_STATUSES)}"
        )

    if status == "OK":
        missing = _REQUIRED_OK_KEYS - set(report.keys())
        if missing:
            raise ValueError(f"missing required keys for OK report: {sorted(missing)}")
    elif status == "BLOCKED":
        missing = _REQUIRED_BLOCKED_KEYS - set(report.keys())
        if missing:
            raise ValueError(
                f"missing required keys for BLOCKED report: {sorted(missing)}"
            )


def validate_guard_report(report: dict) -> None:
    """Full validation: keys, types, values."""
    assert_guard_report_keys(report)

    status = report["status"]

    # type checks common to both
    if not isinstance(report.get("action"), str):
        raise ValueError("action must be str")
    if not isinstance(report.get("env_overrides"), dict):
        raise ValueError("env_overrides must be dict")

    if status == "OK":
        if not isinstance(report.get("mode"), str):
            raise ValueError("mode must be str")
        if not isinstance(report.get("layer0_blocked"), bool):
            raise ValueError("layer0_blocked must be bool")
        if not isinstance(report.get("layer1_capability"), bool):
            raise ValueError("layer1_capability must be bool")
        if not isinstance(report.get("layer2_cli_allow"), bool):
            raise ValueError("layer2_cli_allow must be bool")
        if not isinstance(report.get("layer3_env_unlock"), bool):
            raise ValueError("layer3_env_unlock must be bool")
        if not isinstance(report.get("layer4_manual_confirm"), bool):
            raise ValueError("layer4_manual_confirm must be bool")
        if not isinstance(report.get("layer5_symbol_ok"), bool):
            raise ValueError("layer5_symbol_ok must be bool")

    elif status == "BLOCKED":
        if not isinstance(report.get("reason"), str):
            raise ValueError("reason must be str")
        if not isinstance(report.get("symbol"), str):
            raise ValueError("symbol must be str")


def build_guard_report_summary(report: dict) -> dict:
    """Return a compact stable subset of the report."""
    assert_guard_report_keys(report)
    status = report["status"]
    summary: dict[str, Any] = {
        "blocked": status == "BLOCKED",
        "status": status,
        "action": report["action"],
    }
    if status == "OK":
        summary["mode"] = report["mode"]
        summary["all_layers_pass"] = all([
            not report["layer0_blocked"],
            report["layer1_capability"],
            report["layer2_cli_allow"],
            report["layer3_env_unlock"],
            report["layer4_manual_confirm"],
            report["layer5_symbol_ok"],
        ])
    elif status == "BLOCKED":
        summary["reason"] = report["reason"]
    return summary
