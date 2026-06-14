"""Runner: read-only discovery design."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_discovery"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_discovery"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_discovery.discovery_design")
    design = mod.create_design()
    mod.write_design(design, OUT_DIR / "discovery_design.json")
    report = mod.render_report(design)
    (REPORT_DIR / "discovery_design_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "discovery_design_report.md").write_text(report, encoding="utf-8")
    print(f"discovery_design: {len(design.allowed_methods)} allowed, {len(design.prohibited_methods)} prohibited")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
