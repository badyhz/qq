"""Runner: submit unlock blocker matrix."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "submit_blockers"
REPORT_DIR = ROOT / "reports" / "submit_blockers"

def main() -> int:
    blockers_mod = importlib.import_module("src.runtime_integrations.testnet_enablement.submit_unlock_blocker_matrix")

    blockers = blockers_mod.get_blockers()
    blockers_mod.write_blockers(blockers, OUT_DIR / "submit_blockers.json")
    report = blockers_mod.render_report(blockers)
    (REPORT_DIR / "submit_blockers.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "submit_blockers.md").write_text(report, encoding="utf-8")

    blocking = sum(1 for b in blockers if b.status == "BLOCKING")
    print(f"submit_blockers: {len(blockers)} blockers, {blocking} BLOCKING")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
