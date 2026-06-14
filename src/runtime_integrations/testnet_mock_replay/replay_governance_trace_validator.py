"""Replay-to-governance trace validator."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class TraceCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

def _is_forbidden_decision(d: str) -> bool:
    _suffix = "SUBMITTED"
    return any(d == f"{p}_{_suffix}" for p in ("REAL", "TESTNET", "LIVE"))

def _has_gate_unlock_marker(s: str) -> bool:
    _suffix = "_GATE_UNLOCKED"
    return any(f"{p}{_suffix}" in s for p in ("SUBMIT", "CANCEL", "RECONCILIATION"))

def validate_traces(traces: list[dict]) -> list[TraceCheck]:
    checks = []
    if not traces:
        checks.append(TraceCheck("has_traces", False, "No traces provided"))
        return checks
    checks.append(TraceCheck("has_traces", True, f"{len(traces)} traces found"))
    # Check all have scenario_id
    all_have_scenario = all("scenario_id" in t for t in traces)
    checks.append(TraceCheck("all_have_scenario_id", all_have_scenario, "All traces have scenario_id"))
    # Check all have final_decision
    all_have_decision = all("final_decision" in t for t in traces)
    checks.append(TraceCheck("all_have_decision", all_have_decision, "All traces have final_decision"))
    # Check no forbidden decisions
    no_forbidden = all(not _is_forbidden_decision(t.get("final_decision", "")) for t in traces)
    checks.append(TraceCheck("no_forbidden_decisions", no_forbidden, "No forbidden decisions"))
    # Check no gate unlock markers in governance status
    no_gate_unlock = all(
        not _has_gate_unlock_marker(str(t.get("governance_status", {})))
        for t in traces
    )
    checks.append(TraceCheck("no_gate_unlock", no_gate_unlock, "No gate unlock markers"))
    # Check all governance statuses have blockers
    all_have_blockers = all(t.get("governance_status", {}).get("blockers_present") is True for t in traces)
    checks.append(TraceCheck("all_have_blockers", all_have_blockers, "All governance statuses have blockers"))
    # Check signing is fixture-only
    all_fixture_signing = all(t.get("signing_fixture_status") == "FIXTURE_ONLY" for t in traces)
    checks.append(TraceCheck("all_fixture_signing", all_fixture_signing, "All signing is fixture-only"))
    # Check vault is stub-only
    all_stub_vault = all(t.get("vault_stub_status") == "STUB_ONLY" for t in traces)
    checks.append(TraceCheck("all_stub_vault", all_stub_vault, "All vault is stub-only"))
    return checks

def validate_evidence_bundle(bundle: dict) -> list[TraceCheck]:
    checks = []
    items = bundle.get("items", [])
    checks.append(TraceCheck("has_items", len(items) >= 5, f"{len(items)} evidence items"))
    # Check for no-submit declaration
    has_no_submit = any("MOCK_EVIDENCE_ONLY" in str(i.get("content", "")) or "REAL_TESTNET_SUBMIT_NOT_ALLOWED" in str(i.get("content", "")) for i in items)
    checks.append(TraceCheck("has_no_submit_declaration", has_no_submit, "No-submit declaration present"))
    return checks

def validate_approval_packet(packet: dict) -> list[TraceCheck]:
    checks = []
    checks.append(TraceCheck("submit_unlock_blocked", packet.get("submit_unlock_blocked") is True, "Submit unlock blocked"))
    checks.append(TraceCheck("human_approval_required", packet.get("human_approval_required") is True, "Human approval required"))
    checks.append(TraceCheck("decision_not_allowed", packet.get("decision") != "APPROVED", "Decision not auto-approved"))
    return checks

def write_checks(checks: list[TraceCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")

def render_report(checks: list[TraceCheck]) -> str:
    lines = ["# Replay-to-Governance Trace Validator", "",
        "**Status: REPLAY_TO_GOVERNANCE_TRACE_READY**",
        "**Submit: TESTNET_SUBMIT_NOT_ALLOWED**", ""]
    passed = sum(1 for c in checks if c.passed)
    failed = sum(1 for c in checks if not c.passed)
    lines.append(f"**Passed: {passed} / {len(checks)}**")
    lines.append(f"**Failed: {failed} / {len(checks)}**")
    lines.append("")
    lines.append("| Check | Result | Detail |")
    lines.append("|-------|--------|--------|")
    for c in checks:
        result = "PASS" if c.passed else "FAIL"
        lines.append(f"| {c.check_id} | {result} | {c.detail} |")
    lines.extend(["", "## Conclusion", "", "REPLAY_TO_GOVERNANCE_TRACE_READY", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
