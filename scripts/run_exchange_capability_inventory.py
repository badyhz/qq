"""Runner: exchange capability inventory."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_discovery"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_discovery"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_discovery.exchange_capability_inventory")
    inventory = mod.create_inventory()
    mod.write_inventory(inventory, OUT_DIR / "exchange_capability_inventory.json")
    report = mod.render_report(inventory)
    (REPORT_DIR / "exchange_capability_inventory_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "exchange_capability_inventory_report.md").write_text(report, encoding="utf-8")
    print(f"exchange_capability_inventory: allowed={mod.count_allowed(inventory)}, prohibited={mod.count_prohibited(inventory)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
