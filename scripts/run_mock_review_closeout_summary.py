"""Runner: mock review closeout summary."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_closeout"
REPORT_DIR = ROOT / "reports" / "testnet_mock_closeout"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_mock_closeout.closeout_summary")
    summary = mod.create_summary()
    mod.write_summary(summary, OUT_DIR / "closeout_summary.json")
    report = mod.render_report(summary)
    (REPORT_DIR / "closeout_summary_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "closeout_summary_report.md").write_text(report, encoding="utf-8")
    print(f"closeout_summary: {len(summary.stages)} stages, status={summary.overall_status}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
