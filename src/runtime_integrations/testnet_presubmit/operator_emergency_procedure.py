"""Operator emergency procedure. Defines steps for emergency response."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class EmergencyStep:
    step_id: str
    title: str
    description: str
    required: bool
    def to_dict(self) -> dict:
        return {"step_id": self.step_id, "title": self.title, "description": self.description, "required": self.required}

EMERGENCY_STEPS = (
    EmergencyStep("stop_scheduled", "Stop scheduled dry-run", "Disable all scheduled E2E runs immediately", True),
    EmergencyStep("freeze_intents", "Freeze new submit intents", "Block creation of new submit intent packets", True),
    EmergencyStep("enable_kill_switch", "Enable kill switch", "Set kill switch to ENABLED_BLOCKING", True),
    EmergencyStep("archive_artifacts", "Archive current runtime artifacts", "Copy all runtime artifacts to timestamped archive", True),
    EmergencyStep("export_audit_log", "Export audit log", "Export full audit log for review", True),
    EmergencyStep("review_approvals", "Review pending approvals", "Deny all pending approval requests", True),
    EmergencyStep("confirm_no_real", "Confirm no real orders", "Verify no real orders were submitted", True),
    EmergencyStep("escalation_checklist", "Manual escalation checklist", "Follow escalation procedure", True),
    EmergencyStep("rollback", "Rollback procedure", "Restore to last known good state", True),
    EmergencyStep("post_incident", "Post-incident review", "Document incident and lessons learned", True),
)

def get_steps() -> tuple[EmergencyStep, ...]:
    return EMERGENCY_STEPS

def validate_procedure(steps: tuple[EmergencyStep, ...]) -> tuple[bool, tuple[str, ...]]:
    errors = []
    required_ids = {s.step_id for s in steps if s.required}
    expected = {"stop_scheduled", "freeze_intents", "enable_kill_switch", "archive_artifacts", "export_audit_log", "review_approvals", "confirm_no_real", "escalation_checklist", "rollback", "post_incident"}
    missing = expected - required_ids
    if missing:
        errors.append(f"missing required steps: {missing}")
    return (len(errors) == 0, tuple(errors))

def write_check(valid: bool, errors: tuple[str, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"valid": valid, "errors": list(errors), "step_count": len(EMERGENCY_STEPS)}, indent=2), encoding="utf-8")
