"""Server no-submit regression. Proves server artifacts cannot submit."""
from __future__ import annotations
import json, pathlib
from dataclasses import dataclass

@dataclass(frozen=True)
class ServerSafetyCheck:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}

HIGH_RISK_MODULES = ("core.live_runner", "scripts.live_playbook", "scripts.submit_approved_candidates", "scripts.submit_replayed_testnet_payload", "scripts.run_testnet_order_smoke", "scripts.safe_flatten_testnet_symbol")

def run_server_safety_checks(root: pathlib.Path) -> list[ServerSafetyCheck]:
    checks = []
    # E2E module does not import high-risk
    e2e = root / "src" / "runtime_integrations" / "e2e" / "system_dry_run_e2e.py"
    if e2e.exists():
        content = e2e.read_text()
        for mod in HIGH_RISK_MODULES:
            checks.append(ServerSafetyCheck(f"e2e_no_import_{mod.replace('.','_')}", mod not in content, f"{mod} {'absent' if mod not in content else 'FOUND'}"))
    # Systemd templates
    svc_dir = root / "deployment" / "runtime_dry_run" / "systemd"
    if svc_dir.exists():
        for p in svc_dir.glob("*.example"):
            content = p.read_text()
            for mod in HIGH_RISK_MODULES:
                script_name = mod.split(".")[-1] + ".py"
                checks.append(ServerSafetyCheck(f"template_{p.name}_no_{script_name.replace('.','_')}", script_name not in content, f"{script_name} {'absent' if script_name not in content else 'FOUND'}"))
    # E2E manifest safety
    manifest = root / "data" / "runtime" / "e2e" / "run_manifest.json"
    if manifest.exists():
        m = json.loads(manifest.read_text())
        checks.append(ServerSafetyCheck("manifest_status", "E2E_PASS" in m.get("status", ""), f"status={m.get('status')}"))
    # System state
    state_path = root / "data" / "runtime" / "operator" / "system_state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text())
        checks.append(ServerSafetyCheck("state_real_submit_blocked", not state.get("real_submit_allowed", True), "real_submit_allowed=False"))
        checks.append(ServerSafetyCheck("state_dry_run", state.get("dry_run", False), "dry_run=True"))
    return checks

def write_checks(checks: list[ServerSafetyCheck], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
