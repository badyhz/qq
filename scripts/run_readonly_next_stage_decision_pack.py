"""Runner: readonly next stage decision pack."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_checkpoint"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_checkpoint"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_checkpoint.next_stage_decision_pack")
    pack = mod.create_pack()
    mod.write_pack(pack, OUT_DIR / "next_stage_decision_pack.json")
    report = mod.render_report(pack)
    (REPORT_DIR / "next_stage_decision_pack_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "next_stage_decision_pack_report.md").write_text(report, encoding="utf-8")
    print(f"next_stage_decision_pack: recommended={pack.recommended_next}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
