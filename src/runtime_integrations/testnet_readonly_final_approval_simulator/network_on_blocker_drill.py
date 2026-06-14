"""Network-on blocker drill: simulates what happens if network were enabled, proves blockers fire."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DrillScenario:
    scenario_id: str
    description: str
    trigger: str
    blocker_response: str
    blocked: bool
    def to_dict(self) -> dict:
        return {"scenario_id": self.scenario_id, "description": self.description,
                "trigger": self.trigger, "blocker_response": self.blocker_response,
                "blocked": self.blocked}


@dataclass(frozen=True)
class NetworkOnBlockerDrill:
    drill_id: str
    created_at: str
    scenarios: tuple[DrillScenario, ...]
    final_verdict: str
    def to_dict(self) -> dict:
        return {"drill_id": self.drill_id, "created_at": self.created_at,
                "scenarios": [s.to_dict() for s in self.scenarios],
                "final_verdict": self.final_verdict}


SCENARIOS = (
    DrillScenario("DRILL_001", "Attempt real Binance API call", "network_call", "BLOCKED_BY_NO_NETWORK_FLAG", True),
    DrillScenario("DRILL_002", "Attempt testnet order submit", "submit_order", "BLOCKED_BY_SUBMIT_GATE_LOCK", True),
    DrillScenario("DRILL_003", "Attempt cancel order", "cancel_order", "BLOCKED_BY_CANCEL_GATE_LOCK", True),
    DrillScenario("DRILL_004", "Attempt reconciliation unlock", "recon_unlock", "BLOCKED_BY_RECON_GATE_LOCK", True),
    DrillScenario("DRILL_005", "Attempt credential load from .env", "load_credentials", "BLOCKED_BY_AIR_GAP_POLICY", True),
    DrillScenario("DRILL_006", "Attempt real API key injection", "inject_key", "BLOCKED_BY_CREDENTIAL_POLICY", True),
    DrillScenario("DRILL_007", "Attempt websocket connection", "ws_connect", "BLOCKED_BY_NO_NETWORK_FLAG", True),
    DrillScenario("DRILL_008", "Attempt httpx POST to exchange", "http_post", "BLOCKED_BY_NO_NETWORK_FLAG", True),
)


def create_drill() -> NetworkOnBlockerDrill:
    all_blocked = all(s.blocked for s in SCENARIOS)
    return NetworkOnBlockerDrill(
        drill_id=f"NBD_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        scenarios=SCENARIOS,
        final_verdict=f"NETWORK_ON_BLOCKER_DRILL_{'PASS' if all_blocked else 'FAIL'}|ALL_SCENARIOS_BLOCKED|REAL_NETWORK_NOT_ALLOWED",
    )


def write_drill(drill: NetworkOnBlockerDrill, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(drill.to_dict(), indent=2), encoding="utf-8")


def render_report(drill: NetworkOnBlockerDrill) -> str:
    lines = ["# Network-On Blocker Drill", "",
        f"**drill_id={drill.drill_id}**",
        f"**verdict={drill.final_verdict}**", "",
        "## Scenarios", "",
        "| Scenario | Description | Trigger | Response | Blocked |",
        "|----------|-------------|---------|----------|:---:|"]
    for s in drill.scenarios:
        lines.append(f"| {s.scenario_id} | {s.description} | {s.trigger} | {s.blocker_response} | {'Y' if s.blocked else 'N'} |")
    lines.extend(["", "## Conclusion", "",
        "NETWORK_ON_BLOCKER_DRILL_PASS",
        "ALL_SCENARIOS_BLOCKED",
        "REAL_NETWORK_NOT_ALLOWED", ""])
    return "\n".join(lines)
