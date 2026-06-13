"""Runtime health. Evaluates system health from metrics."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

from src.runtime_integrations.observability.runtime_metrics import RuntimeMetrics


@dataclass(frozen=True)
class RuntimeHealth:
    status: str  # OK, WARN, BLOCKED
    checks: tuple[dict, ...]
    summary: str

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "checks": list(self.checks),
            "summary": self.summary,
        }


def evaluate_health(metrics: RuntimeMetrics) -> RuntimeHealth:
    """Evaluate health from runtime metrics."""
    checks = []
    warnings = 0
    blockers = 0

    def _check(name: str, ok: bool, detail: str):
        nonlocal warnings, blockers
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            warnings += 1

    _check("signals_exist", metrics.signal_count > 0, f"signals={metrics.signal_count}")
    _check("alerts_exist", metrics.alert_count > 0, f"alerts={metrics.alert_count}")
    _check("no_submit_evidence", metrics.no_submit_evidence_count > 0, f"evidence={metrics.no_submit_evidence_count}")
    _check("dashboard_generated", metrics.dashboard_generated, "dashboard HTML exists")
    _check("no_blockers", metrics.blocker_count == 0, f"blockers={metrics.blocker_count}")
    _check("no_warnings", metrics.warning_count == 0, f"warnings={metrics.warning_count}")

    if blockers > 0:
        status = "BLOCKED"
    elif warnings > 0:
        status = "WARN"
    else:
        status = "OK"

    return RuntimeHealth(
        status=status,
        checks=tuple(checks),
        summary=f"status={status}, warnings={warnings}, blockers={blockers}",
    )


def write_health(health: RuntimeHealth, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(health.to_dict(), indent=2), encoding="utf-8")
