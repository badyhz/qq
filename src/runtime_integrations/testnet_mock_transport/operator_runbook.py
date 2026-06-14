"""Operator runbook draft."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class RunbookStep:
    step_id: str
    category: str
    title: str
    content: str
    required: bool
    def to_dict(self) -> dict:
        return {"step_id": self.step_id, "category": self.category, "title": self.title, "content": self.content, "required": self.required}

STEPS = (
    RunbookStep("preflight", "preflight", "Preflight Checklist", "Verify mock transport running, vault stub active, signing fixture valid, no real credentials loaded.", True),
    RunbookStep("mock_transport", "verification", "Mock Transport Verification", "Run mock transport contract test. Verify all fixtures return expected responses.", True),
    RunbookStep("vault_stub", "verification", "Vault Stub Verification", "Run vault stub validator. Verify all credentials are redacted and placeholder.", True),
    RunbookStep("signing_fixture", "verification", "Signing Fixture Verification", "Run signing fixture validator. Verify no real secrets used.", True),
    RunbookStep("no_submit", "verification", "No-Submit Verification", "Run no-submit safety regression. Verify all checks pass.", True),
    RunbookStep("emergency_stop", "emergency", "Emergency Stop Procedure", "Activate kill switch. Cancel all open orders. Freeze new order submission. Notify operator.", True),
    RunbookStep("rollback", "emergency", "Rollback Procedure", "Revert to last known good commit. Disable mock adapter. Re-enable kill switch.", True),
    RunbookStep("evidence", "post", "Evidence Collection", "Collect all test results, audit logs, approval records. Bundle for post-test review.", True),
    RunbookStep("prohibited", "safety", "Prohibited Actions", "No real submit, no real credentials, no real network, no gate unlock without approval.", True),
)

def get_steps() -> tuple[RunbookStep, ...]:
    return STEPS

def write_runbook(steps: tuple[RunbookStep, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([s.to_dict() for s in steps], indent=2), encoding="utf-8")

def render_report(steps: tuple[RunbookStep, ...]) -> str:
    lines = ["# Operator Runbook Draft", "",
        "**runbook_mode=DRAFT_ONLY**",
        "**submit_allowed=false**", ""]
    for s in steps:
        lines.extend([f"## {s.title}", "", s.content, ""])
    lines.extend(["## Conclusion", "", "OPERATOR_RUNBOOK_DRAFT_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
