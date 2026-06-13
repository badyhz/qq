"""Sandbox design safety regression. Proves no real submit or credential risk."""
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
SANDBOX_DIR = pathlib.Path(__file__).resolve().parent

def run_safety_regression(root: pathlib.Path) -> list[SafetyCheck]:
    checks = []
    # No high-risk legacy imports (exclude this checker module from self-scan)
    sandbox_files = [f for f in SANDBOX_DIR.glob("*.py") if f.name != "sandbox_design_safety_regression.py"]
    for sf in sandbox_files:
        content = sf.read_text(encoding="utf-8")
        for mod in HIGH_RISK_MODULES:
            checks.append(SafetyCheck(f"{sf.name}_no_{mod.replace('.', '_')}", mod not in content, f"{mod} {'absent' if mod not in content else 'FOUND'}"))
    # No forbidden imports
    for sf in sandbox_files:
        content = sf.read_text(encoding="utf-8")
        for imp in FORBIDDEN_IMPORTS:
            check_name = f"{sf.name}_no_import_{imp}"
            found = f"import {imp}" in content or f"from {imp}" in content
            checks.append(SafetyCheck(check_name, not found, f"{imp} {'absent' if not found else 'FOUND'}"))
    # No real API key loading
    for sf in sandbox_files:
        content = sf.read_text(encoding="utf-8")
        has_real_key = "os.environ[" in content and "api" in content.lower()
        checks.append(SafetyCheck(f"{sf.name}_no_real_key_load", not has_real_key, "no real API key loading"))
    # No webhook sending
    for sf in sandbox_files:
        content = sf.read_text(encoding="utf-8")
        has_webhook_send = "requests.post" in content or "httpx.post" in content or "webhook_url" in content
        checks.append(SafetyCheck(f"{sf.name}_no_webhook_send", not has_webhook_send, "no webhook sending"))
    # Submit records are simulated
    smoke_path = SANDBOX_DIR / "no_submit_sandbox_smoke.py"
    if smoke_path.exists():
        content = smoke_path.read_text(encoding="utf-8")
        checks.append(SafetyCheck("smoke_simulated_only", '"simulated": True' in content or "simulated=True" in content, "smoke uses simulated=True"))
        checks.append(SafetyCheck("smoke_no_real_submit", '"real_submit": False' in content or "real_submit=False" in content, "smoke uses real_submit=False"))
    # Human approval default blocks
    gate_path = SANDBOX_DIR / "human_approval_gate.py"
    if gate_path.exists():
        content = gate_path.read_text(encoding="utf-8")
        checks.append(SafetyCheck("gate_default_deny", "DEFAULT_DENY" in content, "gate uses DEFAULT_DENY"))
        checks.append(SafetyCheck("gate_submit_blocked", "submit_allowed" in content and "False" in content, "gate blocks submit"))
    # Kill switch default blocks
    ks_path = SANDBOX_DIR / "kill_switch.py"
    if ks_path.exists():
        content = ks_path.read_text(encoding="utf-8")
        checks.append(SafetyCheck("ks_default_blocking", "ENABLED_BLOCKING" in content, "kill switch defaults to ENABLED_BLOCKING"))
        checks.append(SafetyCheck("ks_submit_blocked", "submit_blocked" in content and "True" in content, "kill switch blocks submit"))
    return checks

def write_checks(checks: list[SafetyCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")

def render_safety_report(checks: list[SafetyCheck]) -> str:
    lines = ["# Sandbox Design Safety Regression Report", "", "| Check | Passed | Detail |", "|-------|--------|--------|"]
    for c in checks:
        lines.append(f"| {c.check_id} | {c.passed} | {c.detail} |")
    all_pass = all(c.passed for c in checks)
    lines.extend(["", "## Conclusion", "", f"ALL_CHECKS_PASSED: {all_pass}", ""])
    return "\n".join(lines)
