"""Runner: read-only final approval simulator."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_final_approval_simulator"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_final_approval_simulator"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_final_approval_simulator.final_approval_simulator")
    obj = mod.create_simulation()
    mod.write_simulation(obj, OUT_DIR / "final_approval_simulation.json")
    report = mod.render_report(obj)
    (REPORT_DIR / "final_approval_simulation_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "final_approval_simulation_report.md").write_text(report, encoding="utf-8")
    print(f"read-only final approval simulator: created")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
