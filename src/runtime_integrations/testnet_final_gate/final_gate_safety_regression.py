"""Final gate safety regression. Proves this layer still cannot submit."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class SafetyCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

HIGH_RISK_MODULES = ("core.live_runner", "scripts.live_playbook", "scripts.submit_approved_candidates", "scripts.submit_replayed_testnet_payload", "scripts.run_testnet_order_smoke", "scripts.safe_flatten_testnet_symbol")
FORBIDDEN_IMPORTS = ("ccxt", "requests", "httpx", "aiohttp", "websocket")
GATE_DIR = pathlib.Path(__file__).resolve().parent

def run_regression(root: pathlib.Path) -> list[SafetyCheck]:
    checks = []
    gate_files = [f for f in GATE_DIR.glob("*.py") if f.name != "final_gate_safety_regression.py"]
    # No high-risk imports
    for sf in gate_files:
        content = sf.read_text(encoding="utf-8")
        for mod in HIGH_RISK_MODULES:
            checks.append(SafetyCheck(f"{sf.name}_no_{mod.replace('.', '_')}", mod not in content, f"{mod} {'absent' if mod not in content else 'FOUND'}"))
    # No forbidden imports
    for sf in gate_files:
        content = sf.read_text(encoding="utf-8")
        for imp in FORBIDDEN_IMPORTS:
            found = f"import {imp}" in content or f"from {imp}" in content
            checks.append(SafetyCheck(f"{sf.name}_no_{imp}", not found, f"{imp} {'absent' if not found else 'FOUND'}"))
    # Submit gate locked
    submit_path = GATE_DIR / "submit_gate_final_lock.py"
    if submit_path.exists():
        content = submit_path.read_text(encoding="utf-8")
        checks.append(SafetyCheck("submit_gate_locked", "LOCKED" in content, "submit gate uses LOCKED"))
        checks.append(SafetyCheck("submit_gate_no_real", "real_submit_allowed=False" in content, "real_submit_allowed=False"))
    # Cancel gate locked
    cancel_path = GATE_DIR / "cancel_gate_final_lock.py"
    if cancel_path.exists():
        content = cancel_path.read_text(encoding="utf-8")
        checks.append(SafetyCheck("cancel_gate_locked", "LOCKED" in content, "cancel gate uses LOCKED"))
    # Reconciliation gate locked
    recon_path = GATE_DIR / "reconciliation_gate_final_lock.py"
    if recon_path.exists():
        content = recon_path.read_text(encoding="utf-8")
        checks.append(SafetyCheck("recon_gate_locked", "LOCKED" in content, "reconciliation gate uses LOCKED"))
    # Fake signatures only
    signing_path = GATE_DIR / "request_signing_dry_run.py"
    if signing_path.exists():
        content = signing_path.read_text(encoding="utf-8")
        checks.append(SafetyCheck("signing_dry_run", "DRY_RUN_ONLY" in content, "signing uses DRY_RUN_ONLY"))
        checks.append(SafetyCheck("signing_fake", "fake_signature" in content, "uses fake signature"))
    # Credential injection disabled
    cred_path = GATE_DIR / "credential_injection_review.py"
    if cred_path.exists():
        content = cred_path.read_text(encoding="utf-8")
        checks.append(SafetyCheck("cred_injection_disabled", "credential_injection_allowed=False" in content, "injection disabled"))
    return checks

def write_checks(checks: list[SafetyCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")

def render_report(checks: list[SafetyCheck]) -> str:
    lines = ["# Final Gate Safety Regression Report", "", "| Check | Passed | Detail |", "|-------|--------|--------|"]
    for c in checks:
        lines.append(f"| {c.check_id} | {c.passed} | {c.detail} |")
    lines.extend(["", "## Conclusion", "", f"ALL_PASSED: {all(c.passed for c in checks)}", ""])
    return "\n".join(lines)
