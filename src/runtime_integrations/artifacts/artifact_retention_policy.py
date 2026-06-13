"""Artifact retention policy. Generates retention rules for runtime artifacts."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass


@dataclass(frozen=True)
class RetentionRule:
    artifact_pattern: str
    retention_days: int
    max_count: int
    auto_cleanup: bool

    def to_dict(self) -> dict:
        return {
            "artifact_pattern": self.artifact_pattern,
            "retention_days": self.retention_days,
            "max_count": self.max_count,
            "auto_cleanup": self.auto_cleanup,
        }


DEFAULT_RULES = (
    RetentionRule("data/runtime/e2e/run_manifest.json", 30, 100, False),
    RetentionRule("data/runtime/shadow/signals.jsonl", 7, 50, False),
    RetentionRule("data/runtime/alerts/alerts.jsonl", 30, 100, False),
    RetentionRule("data/runtime/operator/system_state.json", 30, 100, False),
    RetentionRule("reports/operator_dashboard.html", 7, 30, False),
    RetentionRule("reports/system_dry_run_e2e_report.md", 30, 100, False),
)


def get_retention_rules() -> tuple[RetentionRule, ...]:
    return DEFAULT_RULES


def render_retention_policy_markdown() -> str:
    lines = [
        "# Artifact Retention Policy",
        "",
        "| Pattern | Retention | Max Count | Auto Cleanup |",
        "|---------|-----------|-----------|--------------|",
    ]
    for r in DEFAULT_RULES:
        lines.append(f"| {r.artifact_pattern} | {r.retention_days}d | {r.max_count} | {r.auto_cleanup} |")
    lines.append("")
    lines.append("**Note:** Auto cleanup is disabled. Artifacts must be manually reviewed before deletion.")
    lines.append("")
    return "\n".join(lines)


def write_policy(out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_retention_policy_markdown(), encoding="utf-8")
