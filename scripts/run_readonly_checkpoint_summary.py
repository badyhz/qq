"""Runner: readonly checkpoint summary."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_checkpoint"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_checkpoint"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_checkpoint.checkpoint_summary")
    summary = mod.create_summary()
    mod.write_summary(summary, OUT_DIR / "checkpoint_summary.json")
    report = mod.render_report(summary)
    (REPORT_DIR / "checkpoint_summary_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "checkpoint_summary_report.md").write_text(report, encoding="utf-8")
    print(f"checkpoint_summary: {summary.total_stages} stages, latest={summary.latest_commit}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
