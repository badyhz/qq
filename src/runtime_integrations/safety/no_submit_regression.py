"""No-submit regression. Verifies no-submit safety holds in runtime."""
from __future__ import annotations

import json
import pathlib
import sys
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class SafetyCheck:
    check_id: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}


HIGH_RISK_IMPORTS = (
    "core.live_runner",
    "scripts.live_playbook",
    "scripts.submit_approved_candidates",
    "scripts.submit_replayed_testnet_payload",
    "scripts.run_testnet_order_smoke",
    "scripts.safe_flatten_testnet_symbol",
)


def run_safety_checks(data_dir: pathlib.Path, reports_dir: pathlib.Path) -> list[SafetyCheck]:
    """Run no-submit safety regression checks."""
    checks = []

    # Check E2E module imports
    e2e_module = ROOT / "src" / "runtime_integrations" / "e2e" / "system_dry_run_e2e.py"
    if e2e_module.exists():
        content = e2e_module.read_text(encoding="utf-8")
        for mod in HIGH_RISK_IMPORTS:
            checks.append(SafetyCheck(
                check_id=f"no_import_{mod.replace('.', '_')}",
                passed=mod not in content,
                detail=f"Module {mod} {'not imported (good)' if mod not in content else 'imported (BAD)'}",
            ))

    # Check order lifecycle is simulated
    lifecycle = data_dir / "runtime" / "testnet_sim" / "order_lifecycle.jsonl"
    if lifecycle.exists():
        try:
            data = json.loads(lifecycle.read_text(encoding="utf-8"))
            all_simulated = all(item.get("dry_run", False) for item in data)
            all_no_real = all(item.get("no_real_action", False) for item in data)
            checks.append(SafetyCheck("lifecycle_all_dry_run", all_simulated, f"dry_run={all_simulated}"))
            checks.append(SafetyCheck("lifecycle_all_no_real", all_no_real, f"no_real_action={all_no_real}"))
        except (json.JSONDecodeError, TypeError):
            checks.append(SafetyCheck("lifecycle_parseable", False, "Failed to parse"))
    else:
        checks.append(SafetyCheck("lifecycle_exists", False, "order_lifecycle.jsonl missing"))

    # Check no-submit evidence
    evidence = data_dir / "runtime" / "testnet_sim" / "no_submit_evidence.jsonl"
    if evidence.exists():
        checks.append(SafetyCheck("no_submit_evidence_exists", True, "evidence file found"))
    else:
        checks.append(SafetyCheck("no_submit_evidence_exists", False, "evidence file missing"))

    # Check E2E manifest has safety flags
    manifest = data_dir / "runtime" / "e2e" / "run_manifest.json"
    if manifest.exists():
        try:
            m = json.loads(manifest.read_text(encoding="utf-8"))
            checks.append(SafetyCheck("manifest_status_pass", m.get("status") == "SYSTEM_DRY_RUN_E2E_PASS", f"status={m.get('status')}"))
        except (json.JSONDecodeError, TypeError):
            checks.append(SafetyCheck("manifest_parseable", False, "Failed to parse"))

    # Check system state safety
    state_path = data_dir / "runtime" / "operator" / "system_state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        checks.append(SafetyCheck("state_real_submit_blocked", not state.get("real_submit_allowed", True), "real_submit_allowed=False"))
        checks.append(SafetyCheck("state_testnet_submit_blocked", not state.get("testnet_submit_allowed", True), "testnet_submit_allowed=False"))
        checks.append(SafetyCheck("state_dry_run", state.get("dry_run", False), "dry_run=True"))

    # Check dashboard has safety banner
    dash = reports_dir / "operator_dashboard.html"
    if dash.exists():
        html = dash.read_text(encoding="utf-8")
        checks.append(SafetyCheck("dashboard_no_submit_banner", "NOT ALLOWED" in html, "safety banner present"))

    return checks


def write_checks(checks: list[SafetyCheck], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps([c.to_dict() for c in checks], indent=2), encoding="utf-8")
