"""Runner: readiness scorecard."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_closeout"
REPORT_DIR = ROOT / "reports" / "testnet_mock_closeout"

def main() -> int:
    mod = importlib.import_module("src.runtime_integrations.testnet_mock_closeout.readiness_scorecard")
    scorecard = mod.create_scorecard()
    mod.write_scorecard(scorecard, OUT_DIR / "readiness_scorecard.json")
    report = mod.render_report(scorecard)
    (REPORT_DIR / "readiness_scorecard_report.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "readiness_scorecard_report.md").write_text(report, encoding="utf-8")
    print(f"readiness_scorecard: avg={mod.average_score(scorecard)}, mock={mod.mock_readiness(scorecard)}, real={mod.real_readiness(scorecard)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
