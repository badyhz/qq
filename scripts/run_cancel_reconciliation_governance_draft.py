"""Runner: cancel and reconciliation governance draft."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_adapter_spec"
REPORT_DIR = ROOT / "reports" / "testnet_adapter_spec"

def main() -> int:
    gov_mod = importlib.import_module("src.runtime_integrations.testnet_adapter_spec.cancel_reconciliation_governance")

    cancel_items = gov_mod.get_cancel_items()
    recon_items = gov_mod.get_recon_items()
    gov_mod.write_governance(cancel_items, recon_items, OUT_DIR / "cancel_reconciliation_governance.json")
    report = gov_mod.render_report(cancel_items, recon_items)
    (REPORT_DIR / "cancel_reconciliation_governance_draft.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "cancel_reconciliation_governance_draft.md").write_text(report, encoding="utf-8")

    print(f"cancel_reconciliation_governance: {len(cancel_items)} cancel items, {len(recon_items)} recon items")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
