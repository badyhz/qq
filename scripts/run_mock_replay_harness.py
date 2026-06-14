"""Runner: mock replay harness."""
from __future__ import annotations
import importlib, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "runtime" / "testnet_mock_replay"
REPORT_DIR = ROOT / "reports" / "testnet_mock_replay"

def main() -> int:
    harness_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.mock_replay_harness")
    scenario_mod = importlib.import_module("src.runtime_integrations.testnet_mock_replay.replay_scenario_matrix")

    # Run all scenarios through the harness
    scenarios = scenario_mod.get_scenarios()
    traces = []
    for s in scenarios:
        trace = harness_mod.run_replay(
            s.scenario_id, s.method, s.path, s.body,
            s.fixture_name, s.status_code, s.response_body, s.expected_decision
        )
        validation = harness_mod.validate_trace(trace)
        traces.append(trace.to_dict())

    import json
    (OUT_DIR / "replay_traces.json").parent.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "replay_traces.json").write_text(json.dumps(traces, indent=2), encoding="utf-8")

    report = harness_mod.render_report()
    (REPORT_DIR / "mock_replay_harness.md").parent.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "mock_replay_harness.md").write_text(report, encoding="utf-8")

    print(f"mock_replay_harness: {len(traces)} traces replayed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
