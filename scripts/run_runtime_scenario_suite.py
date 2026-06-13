#!/usr/bin/env python3
"""T66501 — Runtime Scenario Suite."""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.scenarios.scenario_runner import run_scenario_suite, write_results, write_report

def main():
    scenarios_dir = ROOT / "tests" / "fixtures" / "runtime_scenarios"
    results = run_scenario_suite(scenarios_dir)
    write_results(results, ROOT / "data" / "runtime" / "scenarios" / "scenario_results.jsonl")
    write_report(results, ROOT / "reports" / "runtime_scenario_suite_report.md")
    passed = sum(1 for r in results if r.status == "PASS")
    print(f"Scenarios: {len(results)} total, {passed} passed")

if __name__ == "__main__":
    main()
