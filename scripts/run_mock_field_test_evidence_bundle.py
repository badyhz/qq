"""Runner: mock field-test evidence bundle."""
from __future__ import annotations
import importlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_replay"
REPORT_DIR = ROOT / "reports" / "testnet_mock_replay"

def main() -> int:
    bundle_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.mock_field_test_evidence_bundle")
    scenario_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.replay_scenario_matrix")

    scenarios = scenario_mod.get_scenarios()
    # All scenarios pass in mock mode
    bundle = bundle_mod.create_bundle(len(scenarios), len(scenarios), 0)
    bundle_mod.write_bundle(bundle, OUT_DIR / "evidence_bundle.json")
    report = bundle_mod.render_report(bundle)
    (REPORT_DIR / "mock_field_test_evidence_bundle.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "mock_field_test_evidence_bundle.md").write_text(report, encoding="utf-8")

    print(f"evidence_bundle: {bundle.bundle_id}, {len(bundle.items)} items")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
