"""Integration tests for scenario suite."""
from __future__ import annotations
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.scenarios.scenario_loader import load_all_scenarios
from src.runtime_integrations.scenarios.scenario_runner import run_scenario


def test_load_all_scenarios():
    scenarios = load_all_scenarios(ROOT / "tests" / "fixtures" / "runtime_scenarios")
    assert len(scenarios) == 5
    names = {s.scenario_name for s in scenarios}
    assert "baseline" in names
    assert "no_signals" in names
    assert "malformed_research" in names


def test_baseline_scenario_passes():
    scenarios = load_all_scenarios(ROOT / "tests" / "fixtures" / "runtime_scenarios")
    baseline = next(s for s in scenarios if s.scenario_name == "baseline")
    result = run_scenario(baseline)
    assert result.status == "PASS"


def test_no_signals_scenario_passes():
    scenarios = load_all_scenarios(ROOT / "tests" / "fixtures" / "runtime_scenarios")
    no_sig = next(s for s in scenarios if s.scenario_name == "no_signals")
    result = run_scenario(no_sig)
    assert result.status in ("PASS", "PASS_WITH_WARNINGS")


def test_malformed_scenario_no_crash():
    scenarios = load_all_scenarios(ROOT / "tests" / "fixtures" / "runtime_scenarios")
    bad = next(s for s in scenarios if s.scenario_name == "malformed_research")
    result = run_scenario(bad)
    assert result.status in ("PASS", "PASS_WITH_WARNINGS")


def test_duplicate_scenario_dedup_works():
    scenarios = load_all_scenarios(ROOT / "tests" / "fixtures" / "runtime_scenarios")
    dups = next(s for s in scenarios if s.scenario_name == "alert_duplicates")
    result = run_scenario(dups)
    assert result.status in ("PASS", "PASS_WITH_WARNINGS")
