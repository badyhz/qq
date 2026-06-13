"""Enablement readiness policy."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ReadinessCriterion:
    criterion_id: str
    description: str
    required: bool
    status: str = "DOCUMENTED"
    def to_dict(self) -> dict:
        return {"criterion_id": self.criterion_id, "description": self.description, "required": self.required, "status": self.status}

CRITERIA = (
    ReadinessCriterion("dry_run_complete", "Dry-run runtime integration complete", True),
    ReadinessCriterion("stabilization_complete", "Runtime stabilization complete", True),
    ReadinessCriterion("server_readiness_complete", "Server dry-run readiness complete", True),
    ReadinessCriterion("sandbox_design_complete", "Testnet sandbox design complete", True),
    ReadinessCriterion("presubmit_review_complete", "Pre-submit review complete", True),
    ReadinessCriterion("final_gate_complete", "Final gate review complete", True),
    ReadinessCriterion("submit_gate_locked", "Submit gate remains locked", True),
    ReadinessCriterion("cancel_gate_locked", "Cancel gate remains locked", True),
    ReadinessCriterion("recon_gate_locked", "Reconciliation gate remains locked", True),
    ReadinessCriterion("no_real_credential_vault", "No real credential vault exists", True),
    ReadinessCriterion("no_real_exchange_adapter", "No real exchange adapter exists", True),
)

def get_criteria() -> tuple[ReadinessCriterion, ...]:
    return CRITERIA

def write_criteria(criteria: tuple[ReadinessCriterion, ...], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in criteria], indent=2), encoding="utf-8")
