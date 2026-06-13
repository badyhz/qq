"""Runtime artifact hygiene policy."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ArtifactPolicy:
    path_pattern: str
    category: str  # COMMITTED_BASELINE, RUNTIME_EPHEMERAL, MILESTONE_REPORT, IGNORE_ALWAYS, SAFETY_EVIDENCE
    git_action: str  # track, ignore, milestone_only
    description: str
    def to_dict(self) -> dict:
        return {"path_pattern": self.path_pattern, "category": self.category, "git_action": self.git_action, "description": self.description}

POLICIES = (
    ArtifactPolicy("data/runtime/e2e/*", "RUNTIME_EPHEMERAL", "ignore", "E2E run artifacts regenerated each run"),
    ArtifactPolicy("data/runtime/shadow/*", "RUNTIME_EPHEMERAL", "ignore", "Shadow signals regenerated each run"),
    ArtifactPolicy("data/runtime/alerts/*", "RUNTIME_EPHEMERAL", "ignore", "Alert events regenerated each run"),
    ArtifactPolicy("data/runtime/testnet_sim/*", "RUNTIME_EPHEMERAL", "ignore", "Testnet simulation artifacts"),
    ArtifactPolicy("data/runtime/operator/*", "RUNTIME_EPHEMERAL", "ignore", "Operator state regenerated each run"),
    ArtifactPolicy("data/runtime/research/*", "RUNTIME_EPHEMERAL", "ignore", "Research artifacts regenerated"),
    ArtifactPolicy("data/runtime/replay/*", "RUNTIME_EPHEMERAL", "ignore", "Replay harness artifacts"),
    ArtifactPolicy("data/runtime/scenarios/*", "RUNTIME_EPHEMERAL", "ignore", "Scenario run results"),
    ArtifactPolicy("data/runtime/artifacts/*", "RUNTIME_EPHEMERAL", "ignore", "Artifact manifest"),
    ArtifactPolicy("data/runtime/observability/*", "RUNTIME_EPHEMERAL", "ignore", "Observability metrics"),
    ArtifactPolicy("data/runtime/safety/*", "SAFETY_EVIDENCE", "milestone_only", "Safety regression evidence"),
    ArtifactPolicy("data/runtime/hygiene/*", "RUNTIME_EPHEMERAL", "ignore", "Hygiene check artifacts"),
    ArtifactPolicy("data/runtime/scheduler/*", "RUNTIME_EPHEMERAL", "ignore", "Scheduler simulation artifacts"),
    ArtifactPolicy("data/runtime/server/*", "RUNTIME_EPHEMERAL", "ignore", "Server readiness artifacts"),
    ArtifactPolicy("data/runtime/stabilization/*", "MILESTONE_REPORT", "milestone_only", "Stabilization suite results"),
    ArtifactPolicy("data/runtime/final_stabilization/*", "MILESTONE_REPORT", "milestone_only", "Final stabilization handoff"),
    ArtifactPolicy("reports/operator_dashboard.html", "RUNTIME_EPHEMERAL", "ignore", "Dashboard regenerated each run"),
    ArtifactPolicy("reports/system_dry_run_e2e_report.md", "RUNTIME_EPHEMERAL", "ignore", "E2E report regenerated"),
    ArtifactPolicy("reports/runtime_*.md", "RUNTIME_EPHEMERAL", "ignore", "Runtime reports regenerated"),
    ArtifactPolicy("reports/final_*.md", "MILESTONE_REPORT", "milestone_only", "Final handoff reports"),
    ArtifactPolicy("reports/server_*.md", "RUNTIME_EPHEMERAL", "ignore", "Server readiness reports"),
    ArtifactPolicy("deployment/runtime_dry_run/*", "COMMITTED_BASELINE", "track", "Deployment templates"),
    ArtifactPolicy("src/runtime_integrations/**", "COMMITTED_BASELINE", "track", "Runtime integration source"),
    ArtifactPolicy("tests/integration/**", "COMMITTED_BASELINE", "track", "Integration tests"),
    ArtifactPolicy("scripts/run_*.py", "COMMITTED_BASELINE", "track", "Runner scripts"),
)

def get_policies() -> tuple[ArtifactPolicy, ...]:
    return POLICIES

def render_policy_markdown() -> str:
    lines = ["# Runtime Artifact Hygiene Policy", "", "| Pattern | Category | Git Action |", "|---------|----------|------------|"]
    for p in POLICIES:
        lines.append(f"| {p.path_pattern} | {p.category} | {p.git_action} |")
    lines.extend(["", "## Rules", "", "- RUNTIME_EPHEMERAL: gitignore, regenerated each run", "- SAFETY_EVIDENCE: commit at milestones only", "- MILESTONE_REPORT: commit at milestones only", "- COMMITTED_BASELINE: always track", ""])
    return "\n".join(lines)

def write_policy_json(policies: tuple[ArtifactPolicy, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([p.to_dict() for p in policies], indent=2), encoding="utf-8")
