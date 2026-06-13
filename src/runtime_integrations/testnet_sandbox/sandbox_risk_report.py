"""Sandbox risk report renderer."""
from __future__ import annotations
from .sandbox_risk_controls import RiskCheckResult

def render_risk_report(checks: list[RiskCheckResult]) -> str:
    lines = ["# Sandbox Risk Control Report", "", "| Check | Passed | Detail |", "|-------|--------|--------|"]
    for c in checks:
        lines.append(f"| {c.check_id} | {c.passed} | {c.detail} |")
    all_pass = all(c.passed for c in checks)
    lines.extend(["", "## Conclusion", "", f"ALL_CHECKS_PASSED: {all_pass}", ""])
    return "\n".join(lines)
