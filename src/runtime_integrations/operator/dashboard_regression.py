"""Dashboard regression check. Validates dashboard stability across runs."""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class RegressionCheck:
    check_name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {"check_name": self.check_name, "passed": self.passed, "detail": self.detail}


REQUIRED_DASHBOARD_FIELDS = (
    "ACTUAL_DRY_RUN",
    "NO_SUBMIT",
    "NOT ALLOWED",
    "HEALTHY",
)

FORBIDDEN_DASHBOARD_PATTERNS = (
    "cdn.",
    "googleapis.com",
    "cloudflare",
    "REAL_SUBMIT_ALLOWED",
    "LIVE_TRADING",
)


def check_dashboard(state_path: pathlib.Path, dashboard_path: pathlib.Path) -> list[RegressionCheck]:
    """Run regression checks on dashboard."""
    checks = []

    # State file exists
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        checks.append(RegressionCheck("state_file_exists", True, "system_state.json found"))

        # State has required fields
        for field in ("current_mode", "submit_permission", "runtime_stats"):
            checks.append(RegressionCheck(
                f"state_has_{field}",
                field in state,
                f"Field {field} {'found' if field in state else 'missing'}",
            ))

        # State safety flags
        checks.append(RegressionCheck("real_submit_blocked", not state.get("real_submit_allowed", True), "real_submit_allowed=False"))
        checks.append(RegressionCheck("dry_run_enabled", state.get("dry_run", False), "dry_run=True"))
    else:
        checks.append(RegressionCheck("state_file_exists", False, "system_state.json missing"))

    # Dashboard exists
    if dashboard_path.exists():
        html = dashboard_path.read_text(encoding="utf-8")
        checks.append(RegressionCheck("dashboard_exists", True, "operator_dashboard.html found"))

        # Required fields
        for field in REQUIRED_DASHBOARD_FIELDS:
            checks.append(RegressionCheck(
                f"dashboard_contains_{field.replace(' ', '_')}",
                field in html,
                f"'{field}' {'found' if field in html else 'missing'}",
            ))

        # Forbidden patterns
        for pattern in FORBIDDEN_DASHBOARD_PATTERNS:
            checks.append(RegressionCheck(
                f"dashboard_no_{pattern.replace('.', '_')}",
                pattern not in html,
                f"'{pattern}' {'absent (good)' if pattern not in html else 'found (BAD)'}",
            ))

        # No external network
        checks.append(RegressionCheck("no_external_network", "http://" not in html and "https://" not in html, "No external URLs"))
    else:
        checks.append(RegressionCheck("dashboard_exists", False, "operator_dashboard.html missing"))

    return checks


def write_regression(checks: list[RegressionCheck], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
