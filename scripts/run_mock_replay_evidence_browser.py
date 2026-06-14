"""Runner: mock replay evidence browser."""
from __future__ import annotations
import importlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_review"
REPORT_DIR = ROOT / "reports" / "testnet_mock_review"

def main() -> int:
    browser_mod = importlib.import_module("src.runtime_integrations.testnet_mock_review.evidence_browser")
    bundle_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.mock_field_test_evidence_bundle")

    bundle = bundle_mod.create_bundle(13, 13, 0)
    bundle_dict = bundle.to_dict()

    # Browse all items
    result = browser_mod.browse_evidence(bundle_dict)
    browser_mod.write_result(result, OUT_DIR / "evidence_browser_result.json")

    # Browse with filters
    filtered = browser_mod.browse_evidence(bundle_dict, [
        {"category": "safety"},
        {"keyword": "MOCK"},
    ])

    report = browser_mod.render_report(result)
    (REPORT_DIR / "evidence_browser_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "evidence_browser_report.md").write_text(report, encoding="utf-8")

    print(f"evidence_browser: {result.total_items} items, {len(result.matched_items)} matched")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
