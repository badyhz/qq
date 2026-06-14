"""Runner: review navigation report."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_review"
REPORT_DIR = ROOT / "reports" / "testnet_mock_review"

def main() -> int:
    nav_mod = importlib.import_module("src.runtime_integrations.testnet_mock_review.review_navigation_report")

    report_obj = nav_mod.create_report()
    nav_mod.write_report(report_obj, OUT_DIR / "review_navigation_report.json")

    report = nav_mod.render_report(report_obj)
    (REPORT_DIR / "review_navigation_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "review_navigation_report.md").write_text(report, encoding="utf-8")

    print(f"review_navigation_report: {len(report_obj.entries)} entries")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
