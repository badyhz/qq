"""Runner: read-only discovery manual review queue."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_preapproval"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_preapproval"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_preapproval.manual_review_queue")
    queue = mod.create_queue()
    mod.write_queue(queue, OUT_DIR / "manual_review_queue.json")
    report = mod.render_report(queue)
    (REPORT_DIR / "manual_review_queue_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "manual_review_queue_report.md").write_text(report, encoding="utf-8")
    print(f"manual_review_queue: {len(queue.items)} items, {mod.count_pending(queue)} pending")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
