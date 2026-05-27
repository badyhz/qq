"""Tests for runtime governance scenario batch evaluator.

Deterministic. No I/O. No network. No timestamps.
"""

import pytest

from core.runtime_governance_scenario_batch_evaluator import (
    RuntimeGovernanceScenarioEvaluation,
    evaluate_runtime_governance_scenario,
    evaluate_runtime_governance_scenario_catalog,
    scenario_evaluations_to_dict,
    scenario_evaluations_to_markdown,
)
from core.runtime_governance_scenario_catalog import (
    build_runtime_governance_scenario_catalog,
)


# ── helpers ────────────────────────────────────────────────────────────


def _default_evaluations():
    return evaluate_runtime_governance_scenario_catalog()


# ── tests ──────────────────────────────────────────────────────────────


class TestEvaluateScenarioCatalog:
    """Evaluate full 8-scenario default catalog."""

    def test_all_8_catalog_scenarios_evaluate(self):
        """All 8 scenarios produce an evaluation without error."""
        catalog = build_runtime_governance_scenario_catalog()
        assert len(catalog) == 8
        evaluations = evaluate_runtime_governance_scenario_catalog()
        assert len(evaluations) == 8
        for e in evaluations:
            assert isinstance(e, RuntimeGovernanceScenarioEvaluation)

    def test_pass_scenario_ok_true(self):
        """The valid_shadow scenario evaluates ok=True."""
        catalog = build_runtime_governance_scenario_catalog()
        pass_scenario = next(s for s in catalog if s.scenario_id == "valid_shadow")
        result = evaluate_runtime_governance_scenario(pass_scenario)
        assert result.ok is True
        assert result.actual_verdict == "PASS"
        assert result.actual_ready_for_runtime is True

    def test_fail_scenario_ok_when_expected_matches(self):
        """A fail scenario evaluates ok=True when actual matches expected."""
        catalog = build_runtime_governance_scenario_catalog()
        fail_scenario = next(s for s in catalog if s.scenario_id == "missing_run_id")
        result = evaluate_runtime_governance_scenario(fail_scenario)
        assert result.ok is True
        assert result.actual_verdict == "FAIL"
        assert result.actual_ready_for_runtime is False

    def test_all_evaluations_ok_for_default_catalog(self):
        """Every scenario in the default catalog evaluates ok=True."""
        evaluations = _default_evaluations()
        failures = [e for e in evaluations if not e.ok]
        assert failures == [], (
            f"Failed scenarios: {[(f.scenario_id, f.notes) for f in failures]}"
        )


class TestSerialization:
    """Deterministic serialization."""

    def test_dict_deterministic(self):
        """Two calls produce identical dicts."""
        evaluations = _default_evaluations()
        d1 = scenario_evaluations_to_dict(evaluations)
        d2 = scenario_evaluations_to_dict(evaluations)
        assert d1 == d2

    def test_dict_structure(self):
        """Dict contains expected keys."""
        d = scenario_evaluations_to_dict(_default_evaluations())
        assert len(d) == 8
        expected_keys = {
            "scenario_id",
            "expected_verdict",
            "actual_verdict",
            "expected_ready_for_runtime",
            "actual_ready_for_runtime",
            "ok",
            "notes",
        }
        for entry in d:
            assert set(entry.keys()) == expected_keys

    def test_markdown_deterministic(self):
        """Two calls produce identical markdown."""
        evaluations = _default_evaluations()
        m1 = scenario_evaluations_to_markdown(evaluations)
        m2 = scenario_evaluations_to_markdown(evaluations)
        assert m1 == m2

    def test_markdown_contains_all_scenario_ids(self):
        """Markdown table includes every scenario_id."""
        md = scenario_evaluations_to_markdown(_default_evaluations())
        for sid in [
            "valid_shadow",
            "valid_dry_run",
            "missing_run_id",
            "missing_adapter_id",
            "submit_blocked_prod",
            "network_blocked_without_explicit_mode",
            "unknown_mode",
            "blocked_policy",
        ]:
            assert sid in md
