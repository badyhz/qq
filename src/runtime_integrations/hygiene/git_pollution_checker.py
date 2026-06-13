"""Git pollution checker. Detects runtime artifacts that would pollute git."""
from __future__ import annotations
import json, pathlib, subprocess
from dataclasses import dataclass

@dataclass(frozen=True)
class PollutionItem:
    path: str
    category: str  # UNTRACKED_RUNTIME, MODIFIED_RUNTIME, SHOULD_BE_IGNORED
    severity: str  # INFO, WARN, BLOCK
    def to_dict(self) -> dict:
        return {"path": self.path, "category": self.category, "severity": self.severity}

EPHEMERAL_PATTERNS = (
    "data/runtime/e2e/", "data/runtime/shadow/", "data/runtime/alerts/",
    "data/runtime/testnet_sim/", "data/runtime/operator/", "data/runtime/research/",
    "data/runtime/replay/", "data/runtime/scenarios/", "data/runtime/artifacts/",
    "data/runtime/observability/", "data/runtime/hygiene/", "data/runtime/scheduler/",
    "data/runtime/server/", "data/runtime/stabilization/",
    "reports/operator_dashboard.html", "reports/system_dry_run_e2e_report.md",
    "reports/runtime_", "reports/server_",
)

HIGH_RISK_FILES = (
    "core/live_runner.py", "scripts/live_playbook.py",
    "scripts/submit_approved_candidates.py", "scripts/submit_replayed_testnet_payload.py",
    "scripts/run_testnet_order_smoke.py", "scripts/safe_flatten_testnet_symbol.py",
)

def check_pollution(root: pathlib.Path) -> list[PollutionItem]:
    items = []
    try:
        result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=root)
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            status = line[:2].strip()
            path = line[3:].strip()
            if any(path.startswith(p) or path == p.rstrip("/") for p in EPHEMERAL_PATTERNS):
                if status in ("??", "M"):
                    items.append(PollutionItem(path, "UNTRACKED_RUNTIME" if status == "??" else "MODIFIED_RUNTIME", "INFO"))
            if path in HIGH_RISK_FILES and status == "??":
                items.append(PollutionItem(path, "SHOULD_BE_IGNORED", "WARN"))
    except FileNotFoundError:
        pass
    return items

def write_check(items: list[PollutionItem], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([i.to_dict() for i in items], indent=2), encoding="utf-8")
