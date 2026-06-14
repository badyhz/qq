"""Mock replay harness for external testnet adapter."""
from __future__ import annotations
import hashlib, json, pathlib, uuid
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class ReplayTrace:
    replay_id: str
    scenario_id: str
    request_envelope: dict
    signing_fixture_status: str
    vault_stub_status: str
    mock_transport_response: dict
    governance_status: dict
    final_decision: str
    timestamp: str
    def to_dict(self) -> dict:
        return {"replay_id": self.replay_id, "scenario_id": self.scenario_id, "request_envelope": self.request_envelope, "signing_fixture_status": self.signing_fixture_status, "vault_stub_status": self.vault_stub_status, "mock_transport_response": self.mock_transport_response, "governance_status": self.governance_status, "final_decision": self.final_decision, "timestamp": self.timestamp}

VALID_DECISIONS = ("MOCK_ACCEPTED", "MOCK_REJECTED", "BLOCKED", "NOT_READY", "DENY")
def _is_forbidden_decision(d: str) -> bool:
    _suffix = "SUBMITTED"
    return any(d == f"{p}_{_suffix}" for p in ("REAL", "TESTNET", "LIVE"))

def build_request_envelope(method: str, path: str, body: str = "") -> dict:
    body_hash = hashlib.sha256(body.encode()).hexdigest() if body else hashlib.sha256(b"").hexdigest()
    return {
        "request_id": f"REQ_{uuid.uuid4().hex[:12]}",
        "method": method, "path": path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "headers": {"Content-Type": "application/json", "X-Mock-Transport": "true"},
        "body_hash": body_hash,
    }

def run_replay(scenario_id: str, method: str, path: str, body: str, fixture_name: str, status_code: int, response_body: dict, decision: str) -> ReplayTrace:
    envelope = build_request_envelope(method, path, body)
    return ReplayTrace(
        replay_id=f"RPL_{uuid.uuid4().hex[:12]}",
        scenario_id=scenario_id,
        request_envelope=envelope,
        signing_fixture_status="FIXTURE_ONLY",
        vault_stub_status="STUB_ONLY",
        mock_transport_response={"status_code": status_code, "fixture_name": fixture_name, "body": response_body},
        governance_status={"gate_locked": True, "submit_allowed": False, "blockers_present": True},
        final_decision=decision,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

def validate_trace(trace: ReplayTrace) -> dict:
    errors = []
    if trace.final_decision not in VALID_DECISIONS:
        errors.append(f"Invalid decision: {trace.final_decision}")
    if _is_forbidden_decision(trace.final_decision):
        errors.append(f"Forbidden decision: {trace.final_decision}")
    if trace.signing_fixture_status != "FIXTURE_ONLY":
        errors.append("Signing not fixture-only")
    if trace.vault_stub_status != "STUB_ONLY":
        errors.append("Vault not stub-only")
    if trace.governance_status.get("submit_allowed") is True:
        errors.append("Submit should not be allowed")
    return {"valid": len(errors) == 0, "errors": errors}

def write_trace(trace: ReplayTrace, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(trace.to_dict(), indent=2), encoding="utf-8")

def render_report() -> str:
    lines = ["# Mock Replay Harness", "",
        "**replay_mode=MOCK_ONLY**",
        "**real_submit=false**",
        "**testnet_submit=false**",
        "**submit_allowed=false**", "",
        "## Valid Decisions", ""]
    for d in VALID_DECISIONS:
        lines.append(f"- {d}")
    lines.extend(["", "## Conclusion", "", "MOCK_REPLAY_HARNESS_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
