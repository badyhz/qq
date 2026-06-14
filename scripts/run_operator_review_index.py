"""Runner: operator review index."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_review"
REPORT_DIR = ROOT / "reports" / "testnet_mock_review"

def main() -> int:
    index_mod = importlib.import_module("src.runtime_integrations.testnet_mock_review.operator_review_index")

    index = index_mod.create_index()
    index_mod.write_index(index, OUT_DIR / "operator_review_index.json")

    report = index_mod.render_report(index)
    (REPORT_DIR / "operator_review_index_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "operator_review_index_report.md").write_text(report, encoding="utf-8")

    print(f"operator_review_index: {len(index.artifacts)} artifacts indexed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
