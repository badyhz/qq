"""Runner: cancel and reconciliation unlock blockers."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "cancel_recon_blockers"
REPORT_DIR = ROOT / "reports" / "cancel_recon_blockers"

def main() -> int:
    blockers_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.cancel_reconciliation_unlock_blockers")

    cancel_blockers = blockers_mod.get_cancel_blockers()
    recon_blockers = blockers_mod.get_recon_blockers()
    blockers_mod.write_cancel_blockers(cancel_blockers, OUT_DIR / "cancel_blockers.json")
    blockers_mod.write_recon_blockers(recon_blockers, OUT_DIR / "recon_blockers.json")
    report = blockers_mod.render_report()
    (REPORT_DIR / "cancel_recon_blockers.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "cancel_recon_blockers.md").write_text(report, encoding="utf-8")

    cancel_blocking = sum(1 for b in cancel_blockers if b.status == "BLOCKING")
    recon_blocking = sum(1 for b in recon_blockers if b.status == "BLOCKING")
    print(f"cancel_blockers: {len(cancel_blockers)} blockers, {cancel_blocking} BLOCKING")
    print(f"recon_blockers: {len(recon_blockers)} blockers, {recon_blocking} BLOCKING")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
