"""Final approval simulator: simulates human approval workflow without real network."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ApprovalCheck:
    check_id: str
    description: str
    simulated_result: str
    requires_human: bool
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "description": self.description,
                "simulated_result": self.simulated_result, "requires_human": self.requires_human}


@dataclass(frozen=True)
class FinalApprovalSimulator:
    simulation_id: str
    created_at: str
    stage: str
    checks: tuple[ApprovalCheck, ...]
    human_decision: str
    final_verdict: str
    def to_dict(self) -> dict:
        return {"simulation_id": self.simulation_id, "created_at": self.created_at,
                "stage": self.stage, "checks": [c.to_dict() for c in self.checks],
                "human_decision": self.human_decision, "final_verdict": self.final_verdict}


CHECKS = (
    ApprovalCheck("SIM_001", "Prior milestone suites all passed", "PASS", False),
    ApprovalCheck("SIM_002", "Release gate criteria all satisfied", "PASS", False),
    ApprovalCheck("SIM_003", "Network-off execution verified", "PASS", False),
    ApprovalCheck("SIM_004", "Credential air-gap enforced", "PASS", False),
    ApprovalCheck("SIM_005", "Blocker ledger reviewed", "PASS", False),
    ApprovalCheck("SIM_006", "Operator signoff draft prepared", "PASS", False),
    ApprovalCheck("SIM_007", "Safety regression clean", "PASS", False),
    ApprovalCheck("SIM_008", "No real network calls possible", "PASS", False),
    ApprovalCheck("SIM_009", "No testnet submit possible", "PASS", False),
    ApprovalCheck("SIM_010", "Human final approval", "SIMULATED_PENDING", True),
)


def create_simulation() -> FinalApprovalSimulator:
    return FinalApprovalSimulator(
        simulation_id=f"FAS_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        stage="T275001-T290000",
        checks=CHECKS,
        human_decision="SIMULATED_PENDING",
        final_verdict="READONLY_FINAL_APPROVAL_SIMULATOR_READY|HUMAN_DECISION_SIMULATED|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def write_simulation(sim: FinalApprovalSimulator, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sim.to_dict(), indent=2), encoding="utf-8")


def render_report(sim: FinalApprovalSimulator) -> str:
    lines = ["# Read-Only Final Approval Simulator", "",
        f"**simulation_id={sim.simulation_id}**",
        f"**stage={sim.stage}**",
        f"**verdict={sim.final_verdict}**", "",
        "## Approval Checks", "",
        "| Check | Description | Result | Human Required |",
        "|-------|-------------|--------|:---:|"]
    for c in sim.checks:
        lines.append(f"| {c.check_id} | {c.description} | {c.simulated_result} | {'Y' if c.requires_human else 'N'} |")
    lines.extend(["", "## Conclusion", "",
        "READONLY_FINAL_APPROVAL_SIMULATOR_READY",
        "HUMAN_DECISION_SIMULATED",
        "REAL_NETWORK_NOT_ALLOWED",
        "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
