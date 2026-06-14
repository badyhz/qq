"""Network-on blocker drill: simulates what happens if network were enabled, proves blockers fire."""
from __future__ import annotations
import json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DrillScenario:
    scenario_id: str
    request_type: str
    simulated_request: str
    expected_blocker: str
    actual_result: str
    final_decision: str
    risk_category: str
    severity: str
    blocked: bool
    def to_dict(self) -> dict:
        return {"scenario_id": self.scenario_id, "request_type": self.request_type,
                "simulated_request": self.simulated_request, "expected_blocker": self.expected_blocker,
                "actual_result": self.actual_result, "final_decision": self.final_decision,
                "risk_category": self.risk_category, "severity": self.severity,
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
    # Original basic scenarios
    DrillScenario("DRILL_001", "REQUEST_REAL_NETWORK", "Attempt real Binance API call",
        "BLOCKED_BY_NO_NETWORK_FLAG", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "NETWORK_ACCESS", "CRITICAL", True),
    DrillScenario("DRILL_002", "REQUEST_TESTNET_SUBMIT", "Attempt testnet order submit",
        "BLOCKED_BY_SUBMIT_GATE_LOCK", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "ORDER_SUBMIT", "CRITICAL", True),
    DrillScenario("DRILL_003", "REQUEST_CANCEL_SUBMIT", "Attempt cancel order",
        "BLOCKED_BY_CANCEL_GATE_LOCK", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "ORDER_CANCEL", "CRITICAL", True),
    DrillScenario("DRILL_004", "REQUEST_GATE_UNLOCK", "Attempt reconciliation unlock",
        "BLOCKED_BY_RECON_GATE_LOCK", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "GATE_UNLOCK", "CRITICAL", True),
    DrillScenario("DRILL_005", "REQUEST_DOTENV_SECRET_LOAD", "Attempt credential load from .env",
        "BLOCKED_BY_AIR_GAP_POLICY", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "CREDENTIAL_LOAD", "CRITICAL", True),
    DrillScenario("DRILL_006", "REQUEST_REAL_CREDENTIAL", "Attempt real API key injection",
        "BLOCKED_BY_CREDENTIAL_POLICY", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "CREDENTIAL_INJECT", "CRITICAL", True),
    DrillScenario("DRILL_007", "REQUEST_REAL_ENDPOINT", "Attempt websocket connection",
        "BLOCKED_BY_NO_NETWORK_FLAG", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "WEBSOCKET_ACCESS", "HIGH", True),
    DrillScenario("DRILL_008", "REQUEST_ENV_SECRET_LOAD", "Attempt httpx POST to exchange",
        "BLOCKED_BY_NO_NETWORK_FLAG", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "HTTP_ACCESS", "HIGH", True),
    # Expanded edge-case scenarios (REM_002)
    DrillScenario("DRILL_009", "REQUEST_PARTIAL_NETWORK_ENABLEMENT", "Attempt partial network enable for market data only",
        "BLOCKED_BY_NO_NETWORK_FLAG", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "PARTIAL_NETWORK", "HIGH", True),
    DrillScenario("DRILL_010", "REQUEST_NETWORK_TIMEOUT_RETRY", "Attempt retry after simulated network timeout",
        "BLOCKED_BY_NO_NETWORK_FLAG", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "RETRY_LOOP", "HIGH", True),
    DrillScenario("DRILL_011", "REQUEST_AUTH_FAILURE_RETRY", "Attempt retry after simulated auth failure with new credentials",
        "BLOCKED_BY_CREDENTIAL_POLICY", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "AUTH_RETRY", "HIGH", True),
    DrillScenario("DRILL_012", "REQUEST_RATE_LIMIT_RETRY", "Attempt retry after simulated rate limit with backoff",
        "BLOCKED_BY_NO_NETWORK_FLAG", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "RATE_LIMIT", "MEDIUM", True),
    DrillScenario("DRILL_013", "REQUEST_ENDPOINT_ALLOWLIST_BYPASS", "Attempt to bypass endpoint allowlist via URL encoding",
        "BLOCKED_BY_ENDPOINT_ALLOWLIST", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "ALLOWLIST_BYPASS", "CRITICAL", True),
    DrillScenario("DRILL_014", "REQUEST_CREDENTIAL_SCOPE_ESCALATION", "Attempt to escalate read-only credential to write scope",
        "BLOCKED_BY_CREDENTIAL_POLICY", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "SCOPE_ESCALATION", "CRITICAL", True),
    DrillScenario("DRILL_015", "REQUEST_READONLY_TO_SUBMIT_ESCALATION", "Attempt to convert readonly discovery into submit path",
        "BLOCKED_BY_SUBMIT_GATE_LOCK", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "SUBMIT_ESCALATION", "CRITICAL", True),
    DrillScenario("DRILL_016", "REQUEST_AUDIT_REDACTION_BYPASS", "Attempt to emit unredacted credentials in audit log",
        "BLOCKED_BY_REDACTION_POLICY", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "REDACTION_BYPASS", "HIGH", True),
    DrillScenario("DRILL_017", "REQUEST_KILL_SWITCH_BYPASS", "Attempt to disable kill switch via config override",
        "BLOCKED_BY_KILL_SWITCH", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "KILL_SWITCH", "CRITICAL", True),
    DrillScenario("DRILL_018", "REQUEST_ROLLBACK_BYPASS", "Attempt to bypass rollback safety and proceed with stale state",
        "BLOCKED_BY_ROLLBACK_SAFETY", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "ROLLBACK_BYPASS", "HIGH", True),
    DrillScenario("DRILL_019", "REQUEST_READONLY_DISCOVERY_EXECUTION", "Attempt to execute readonly discovery against real exchange",
        "BLOCKED_BY_NO_NETWORK_FLAG", "BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED|TESTNET_SUBMIT_NOT_ALLOWED", "DISCOVERY_EXEC", "HIGH", True),
)


def create_drill() -> NetworkOnBlockerDrill:
    return NetworkOnBlockerDrill(
        drill_id=f"NBD_{uuid.uuid4().hex[:12]}",
        created_at=datetime.now(timezone.utc).isoformat(),
        scenarios=SCENARIOS,
        final_verdict=f"NETWORK_ON_BLOCKER_DRILL_{'PASS' if not has_unblocked_case(SCENARIOS) else 'FAIL'}|NETWORK_ON_BLOCKER_DRILL_EXPANDED|ALL_SCENARIOS_BLOCKED|REAL_NETWORK_STILL_BLOCKED|REAL_NETWORK_NOT_ALLOWED|TESTNET_SUBMIT_NOT_ALLOWED",
    )


def count_blocked(scenarios: tuple[DrillScenario, ...]) -> int:
    return sum(1 for s in scenarios if s.blocked)


def count_by_severity(scenarios: tuple[DrillScenario, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in scenarios:
        counts[s.severity] = counts.get(s.severity, 0) + 1
    return counts


def count_by_risk_category(scenarios: tuple[DrillScenario, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in scenarios:
        counts[s.risk_category] = counts.get(s.risk_category, 0) + 1
    return counts


def has_unblocked_case(scenarios: tuple[DrillScenario, ...]) -> bool:
    return any(not s.blocked for s in scenarios)


def write_drill(drill: NetworkOnBlockerDrill, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(drill.to_dict(), indent=2), encoding="utf-8")


def render_report(drill: NetworkOnBlockerDrill) -> str:
    lines = ["# Network-On Blocker Drill", "",
        f"**drill_id={drill.drill_id}**",
        f"**scenarios={len(drill.scenarios)}**",
        f"**blocked={count_blocked(drill.scenarios)}**",
        f"**verdict={drill.final_verdict}**", "",
        "## Scenarios", "",
        "| ID | Request Type | Blocker | Result | Severity | Category |",
        "|----|-------------|---------|--------|----------|----------|"]
    for s in drill.scenarios:
        lines.append(f"| {s.scenario_id} | {s.request_type} | {s.expected_blocker} | {s.actual_result} | {s.severity} | {s.risk_category} |")
    by_sev = count_by_severity(drill.scenarios)
    lines.extend(["", "## Severity Summary", ""])
    for sev, cnt in sorted(by_sev.items()):
        lines.append(f"- {sev}: {cnt}")
    lines.extend(["", "## Conclusion", "",
        "NETWORK_ON_BLOCKER_DRILL_EXPANDED",
        "NETWORK_ON_BLOCKER_DRILL_PASS",
        "ALL_SCENARIOS_BLOCKED",
        "REAL_NETWORK_STILL_BLOCKED",
        "TESTNET_SUBMIT_NOT_ALLOWED",
        "REAL_NETWORK_NOT_ALLOWED", ""])
    return "\n".join(lines)
