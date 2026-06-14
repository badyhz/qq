"""Runner: read-only adapter contract."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_discovery"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_discovery"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_discovery.readonly_adapter_contract")
    contract = mod.create_contract()
    validation = mod.validate_contract(contract)
    mod.write_contract(contract, OUT_DIR / "readonly_adapter_contract.json")
    report = mod.render_report(contract)
    (REPORT_DIR / "readonly_adapter_contract_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "readonly_adapter_contract_report.md").write_text(report, encoding="utf-8")
    print(f"readonly_adapter_contract: {len(contract.methods)} methods, valid={validation[0]['valid']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
