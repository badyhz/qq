"""Runner: replay scenario matrix."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_replay"
REPORT_DIR = ROOT / "reports" / "testnet_mock_replay"

def main() -> int:
    scenario_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.replay_scenario_matrix")

    scenarios = scenario_mod.get_scenarios()
    scenario_mod.write_scenarios(scenarios, OUT_DIR / "replay_scenario_matrix.json")
    report = scenario_mod.render_report(scenarios)
    (REPORT_DIR / "replay_scenario_matrix.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "replay_scenario_matrix.md").write_text(report, encoding="utf-8")

    print(f"replay_scenario_matrix: {len(scenarios)} scenarios")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
