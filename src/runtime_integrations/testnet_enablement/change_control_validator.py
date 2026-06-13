"""Change control validator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ProposalCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def validate_proposal(proposal: dict) -> list[ProposalCheck]:
    checks = []
    checks.append(ProposalCheck("has_scope", bool(proposal.get("scope")), "scope present"))
    checks.append(ProposalCheck("has_non_goals", len(proposal.get("non_goals", [])) >= 3, "non-goals listed"))
    checks.append(ProposalCheck("has_risk", bool(proposal.get("risk_assessment")), "risk assessment present"))
    checks.append(ProposalCheck("has_security", len(proposal.get("security_requirements", [])) >= 3, "security requirements listed"))
    checks.append(ProposalCheck("has_rollback", bool(proposal.get("rollback_plan")), "rollback plan present"))
    checks.append(ProposalCheck("has_kill_switch", bool(proposal.get("kill_switch_procedure")), "kill switch procedure present"))
    checks.append(ProposalCheck("has_go_no_go", len(proposal.get("go_no_go_checklist", [])) >= 3, "go/no-go checklist present"))
    checks.append(ProposalCheck("no_real_submit_in_non_goals", any("no real submit" in ng.lower() for ng in proposal.get("non_goals", [])), "no real submit in non-goals"))
    return checks

def write_checks(checks: list[ProposalCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
