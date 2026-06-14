"""Runner: readonly suite depth review."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_readonly_scope_audit"
REPORT_DIR = ROOT / "reports" / "testnet_readonly_scope_audit"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_readonly_scope_audit.suite_depth_review")
    review = mod.create_review()
    mod.write_review(review, OUT_DIR / "suite_depth_review.json")
    report = mod.render_report(review)
    (REPORT_DIR / "suite_depth_review_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "suite_depth_review_report.md").write_text(report, encoding="utf-8")
    print(f"suite_depth_review: {len(review.items)} suites reviewed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
