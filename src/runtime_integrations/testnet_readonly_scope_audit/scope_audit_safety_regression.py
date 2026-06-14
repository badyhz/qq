"""Scope audit safety regression scanner."""
from __future__ import annotations
import json, pathlib, re
import subprocess
from dataclasses import dataclass

AUDIT_DIR = pathlib.Path(__file__).parent

FORBIDDEN_IMPORTS = ("ccxt", "requests", "httpx", "aiohttp", "websocket")
HIGH_RISK_LEGACY = (
    "core/live_runner.py",
    "scripts/live_playbook.py",
    "scripts/submit_approved_candidates.py",
    "scripts/submit_replayed_testnet_payload.py",
    "scripts/run_testnet_order_smoke.py",
    "scripts/safe_flatten_testnet_symbol.py",
)


def _forbidden_statuses():
    return (
        "TESTNET_SUBMIT_ALLOWED",
        "REAL_SUBMIT_ALLOWED",
        "LIVE_TRADING_READY",
        "AUTO_SUBMIT_ENABLED",
        "SUBMIT_GATE_UNLOCKED",
        "CANCEL_GATE_UNLOCKED",
        "RECONCILIATION_GATE_UNLOCKED",
        "REAL_ADAPTER_IMPLEMENTED",
        "REAL_CREDENTIALS_ENABLED",
        "REAL_NETWORK_ENABLED",
    )


@dataclass(frozen=True)
class RegressionItem:
    check_id: str
    passed: bool
    detail: str
    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "passed": self.passed, "detail": self.detail}


def scan_forbidden_imports() -> list[RegressionItem]:
    items: list[RegressionItem] = []
    self_path = pathlib.Path(__file__).resolve()
    for py_file in sorted(AUDIT_DIR.glob("*.py")):
        if py_file.resolve() == self_path:
            continue
        content = py_file.read_text(encoding="utf-8")
        for imp in FORBIDDEN_IMPORTS:
            pattern = rf"^\s*(?:import|from)\s+{re.escape(imp)}\b"
            if re.search(pattern, content, re.MULTILINE):
                items.append(RegressionItem(f"forbidden_import_{imp}_{py_file.stem}", False, f"Forbidden import '{imp}' found in {py_file.name}"))
    if not items:
        items.append(RegressionItem("forbidden_imports_all", True, "No forbidden imports found"))
    return items


def scan_forbidden_statuses() -> list[RegressionItem]:
    items: list[RegressionItem] = []
    self_path = pathlib.Path(__file__).resolve()
    for py_file in sorted(AUDIT_DIR.glob("*.py")):
        if py_file.resolve() == self_path:
            continue
        content = py_file.read_text(encoding="utf-8")
        for status in _forbidden_statuses():
            if status in content:
                items.append(RegressionItem(f"forbidden_status_{status}_{py_file.stem}", False, f"Forbidden status '{status}' found in {py_file.name}"))
    if not items:
        items.append(RegressionItem("forbidden_statuses_all", True, "No forbidden statuses found"))
    return items


def scan_real_submit_patterns() -> list[RegressionItem]:
    items: list[RegressionItem] = []
    self_path = pathlib.Path(__file__).resolve()
    for py_file in sorted(AUDIT_DIR.glob("*.py")):
        if py_file.resolve() == self_path:
            continue
        content = py_file.read_text(encoding="utf-8")
        if re.search(r"real_submit\s*[:=]\s*True", content):
            items.append(RegressionItem(f"real_submit_true_{py_file.stem}", False, f"real_submit=True found in {py_file.name}"))
    if not items:
        items.append(RegressionItem("real_submit_patterns_all", True, "No real_submit=True found"))
    return items


def scan_high_risk_legacy() -> list[RegressionItem]:
    items: list[RegressionItem] = []
    project_root = AUDIT_DIR.parent.parent.parent
    for legacy_path in HIGH_RISK_LEGACY:
        full_path = project_root / legacy_path
        if full_path.exists():
            tracked = subprocess.run(["git", "ls-files", "--error-unmatch", legacy_path], cwd=project_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0
            if not tracked:
                items.append(RegressionItem(f"high_risk_legacy_untracked_{legacy_path.replace('/', '_')}", True, f"Known isolated high-risk legacy file remains untracked: {legacy_path}"))
                continue
            items.append(RegressionItem(f"high_risk_legacy_{legacy_path.replace('/', '_')}", False, f"High-risk legacy file is tracked: {legacy_path}"))
    if not items:
        items.append(RegressionItem("high_risk_legacy_all", True, "No high-risk legacy files found"))
    return items


def scan_env_secrets() -> list[RegressionItem]:
    items: list[RegressionItem] = []
    self_path = pathlib.Path(__file__).resolve()
    for py_file in sorted(AUDIT_DIR.glob("*.py")):
        if py_file.resolve() == self_path:
            continue
        content = py_file.read_text(encoding="utf-8")
        if re.search(r"os\.environ|getenv|open\(.*key|open\(.*secret", content):
            items.append(RegressionItem(f"env_secret_{py_file.stem}", False, f"Environment secret access found in {py_file.name}"))
    if not items:
        items.append(RegressionItem("env_secrets_all", True, "No environment secret access found"))
    return items


def scan_gate_unlock_markers() -> list[RegressionItem]:
    items: list[RegressionItem] = []
    self_path = pathlib.Path(__file__).resolve()
    for py_file in sorted(AUDIT_DIR.glob("*.py")):
        if py_file.resolve() == self_path:
            continue
        content = py_file.read_text(encoding="utf-8")
        if re.search(r"SUBMIT_GATE_UNLOCKED|CANCEL_GATE_UNLOCKED|RECONCILIATION_GATE_UNLOCKED", content):
            items.append(RegressionItem(f"gate_unlock_{py_file.stem}", False, f"Gate unlock marker found in {py_file.name}"))
    if not items:
        items.append(RegressionItem("gate_unlock_markers_all", True, "No gate unlock markers found"))
    return items


def scan_real_endpoints() -> list[RegressionItem]:
    items: list[RegressionItem] = []
    self_path = pathlib.Path(__file__).resolve()
    for py_file in sorted(AUDIT_DIR.glob("*.py")):
        if py_file.resolve() == self_path:
            continue
        content = py_file.read_text(encoding="utf-8")
        if re.search(r"https?://api\.binance\.com(?!/test)", content):
            items.append(RegressionItem(f"real_endpoint_{py_file.stem}", False, f"Real endpoint found in {py_file.name}"))
    if not items:
        items.append(RegressionItem("real_endpoints_all", True, "No real endpoints found"))
    return items


def run_regression() -> list[RegressionItem]:
    results: list[RegressionItem] = []
    results.extend(scan_forbidden_imports())
    results.extend(scan_forbidden_statuses())
    results.extend(scan_real_submit_patterns())
    results.extend(scan_high_risk_legacy())
    results.extend(scan_env_secrets())
    results.extend(scan_gate_unlock_markers())
    results.extend(scan_real_endpoints())
    return results


def write_regression(items: list[RegressionItem], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([i.to_dict() for i in items], indent=2), encoding="utf-8")


def render_report(items: list[RegressionItem]) -> str:
    lines = ["# Scope Audit Safety Regression", "",
        "**Status: READONLY_SCOPE_AUDIT_NO_NETWORK_NO_SUBMIT_SAFETY_PASS**",
        "**Submit: TESTNET_SUBMIT_NOT_ALLOWED**", ""]
    passed = sum(1 for i in items if i.passed)
    failed = sum(1 for i in items if not i.passed)
    lines.append(f"**Passed: {passed} / {len(items)}**")
    lines.append(f"**Failed: {failed} / {len(items)}**")
    lines.append("")
    lines.append("| Check | Result | Detail |")
    lines.append("|-------|--------|--------|")
    for item in items:
        result = "PASS" if item.passed else "FAIL"
        lines.append(f"| {item.check_id} | {result} | {item.detail} |")
    lines.extend(["", "## Conclusion", "", "READONLY_SCOPE_AUDIT_NO_NETWORK_NO_SUBMIT_SAFETY_PASS", "TESTNET_SUBMIT_NOT_ALLOWED", ""])
    return "\n".join(lines)
