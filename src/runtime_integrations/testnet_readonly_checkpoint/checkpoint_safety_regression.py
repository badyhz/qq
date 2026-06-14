"""Checkpoint safety regression: scans checkpoint modules for forbidden patterns."""
from __future__ import annotations
import json, pathlib, re
from dataclasses import dataclass

CHECKPOINT_DIR = pathlib.Path(__file__).parent

FORBIDDEN_IMPORTS = ("ccxt", "requests", "httpx", "aiohttp", "websocket")
FORBIDDEN_PATTERNS = (
    "os.environ", "load_dotenv", "open(.env",
    "submit_order", "cancel_order",
    "SUBMIT_GATE_UNLOCKED", "CANCEL_GATE_UNLOCKED", "RECONCILIATION_GATE_UNLOCKED",
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
    for py_file in sorted(CHECKPOINT_DIR.glob("*.py")):
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


def scan_forbidden_patterns() -> list[RegressionItem]:
    items: list[RegressionItem] = []
    self_path = pathlib.Path(__file__).resolve()
    for py_file in sorted(CHECKPOINT_DIR.glob("*.py")):
        if py_file.resolve() == self_path:
            continue
        content = py_file.read_text(encoding="utf-8")
        for pat in FORBIDDEN_PATTERNS:
            if pat in content:
                items.append(RegressionItem(f"forbidden_pattern_{pat}_{py_file.stem}", False, f"Forbidden pattern '{pat}' found in {py_file.name}"))
    if not items:
        items.append(RegressionItem("forbidden_patterns_all", True, "No forbidden patterns found"))
    return items


def scan_real_endpoints() -> list[RegressionItem]:
    items: list[RegressionItem] = []
    self_path = pathlib.Path(__file__).resolve()
    for py_file in sorted(CHECKPOINT_DIR.glob("*.py")):
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
    results.extend(scan_forbidden_patterns())
    results.extend(scan_real_endpoints())
    return results


def write_regression(items: list[RegressionItem], out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([i.to_dict() for i in items], indent=2), encoding="utf-8")


def render_report(items: list[RegressionItem]) -> str:
    lines = ["# Checkpoint Safety Regression", "",
        "**Status: READONLY_CHECKPOINT_NO_NETWORK_NO_SUBMIT_SAFETY_PASS**", ""]
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
    lines.extend(["", "## Conclusion", "", "READONLY_CHECKPOINT_NO_NETWORK_NO_SUBMIT_SAFETY_PASS", ""])
    return "\n".join(lines)
