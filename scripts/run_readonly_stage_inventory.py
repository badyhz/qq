"""Runner: readonly stage inventory."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_scope_audit"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_scope_audit"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_scope_audit.stage_inventory")
    inventory = mod.create_inventory()
    mod.write_inventory(inventory, OUT_DIR / "stage_inventory.json")
    report = mod.render_report(inventory)
    (REPORT_DIR / "stage_inventory_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "stage_inventory_report.md").write_text(report, encoding="utf-8")
    print(f"stage_inventory: {len(inventory.stages)} stages cataloged")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
