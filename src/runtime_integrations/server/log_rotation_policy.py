"""Log rotation policy. Defines retention rules for runtime artifacts."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class RetentionRule:
    artifact_type: str
    max_age_days: int
    max_count: int
    auto_cleanup: bool
    safety_exception: bool
    def to_dict(self) -> dict:
        return {"artifact_type": self.artifact_type, "max_age_days": self.max_age_days, "max_count": self.max_count, "auto_cleanup": self.auto_cleanup, "safety_exception": self.safety_exception}

RULES = (
    RetentionRule("e2e_run_output", 7, 50, False, False),
    RetentionRule("shadow_signals", 3, 30, False, False),
    RetentionRule("alert_events", 30, 100, False, False),
    RetentionRule("operator_state", 7, 50, False, False),
    RetentionRule("dashboard_html", 7, 30, False, False),
    RetentionRule("safety_evidence", 365, 1000, False, True),
    RetentionRule("scheduler_logs", 30, 100, False, False),
    RetentionRule("testnet_simulation", 7, 50, False, False),
)

def get_rules() -> tuple[RetentionRule, ...]:
    return RULES

def render_log_rotation_markdown() -> str:
    lines = ["# Log Rotation Policy", "", "| Artifact | Max Age | Max Count | Auto Cleanup | Safety Exception |", "|----------|---------|-----------|--------------|------------------|"]
    for r in RULES:
        lines.append(f"| {r.artifact_type} | {r.max_age_days}d | {r.max_count} | {r.auto_cleanup} | {r.safety_exception} |")
    lines.extend(["", "**Note:** Auto cleanup is disabled by default. Safety evidence is never auto-deleted.", ""])
    return "\n".join(lines)

def write_rules(rules: tuple[RetentionRule, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.to_dict() for r in rules], indent=2), encoding="utf-8")
