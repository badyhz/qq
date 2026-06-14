"""Runner: read-only release gate safety regression."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_release_gate"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_release_gate"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_release_gate.release_gate_safety_regression")
    items = mod.run_regression()
    mod.write_regression(items, OUT_DIR / "release_gate_safety_regression.json")
    report = mod.render_report(items)
    (REPORT_DIR / "release_gate_safety_regression_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "release_gate_safety_regression_report.md").write_text(report, encoding="utf-8")
    failed = [i for i in items if not i.passed]
    print(f"release_gate_safety_regression: {len(items)} checks, {len(failed)} failed")
    return 0 if len(failed) == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
