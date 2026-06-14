"""Runner: exchange response fixtures."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_transport"
REPORT_DIR = ROOT / "reports" / "testnet_mock_transport"

def main() -> int:
    fixtures_mod = importlib.import_module("src.runtime_integrations.testnet_mock_transport.exchange_response_fixtures")

    fixtures = fixtures_mod.get_fixtures()
    fixtures_mod.write_fixtures(fixtures, OUT_DIR / "exchange_response_fixtures.json")
    report = fixtures_mod.render_report(fixtures)
    (REPORT_DIR / "exchange_response_fixtures.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "exchange_response_fixtures.md").write_text(report, encoding="utf-8")

    print(f"exchange_response_fixtures: {len(fixtures)} fixtures")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
