"""Tests for T834 — Runtime governance read-only scenario evaluator."""

from core.runtime_governance_readonly_scenario_evaluator import (
    RuntimeGovernanceReadOnlyScenarioEvaluation,
    evaluate_readonly_scenario,
    evaluate_readonly_scenario_catalog,
    readonly_evaluations_to_dict,
    readonly_evaluations_to_markdown,
)


class TestEvaluateReadonlyScenarioCatalog:
    """All 6 scenarios evaluate correctly."""

    def test_catalog_returns_6_evaluations(self):
        results = evaluate_readonly_scenario_catalog()
        assert len(results) == 6

    def test_unsafe_scenarios_are_blocked(self):
        results = evaluate_readonly_scenario_catalog()
        unsafe = [r for r in results if r.scenario_id != "safe_summary_read"]
        assert len(unsafe) == 5
        for r in unsafe:
            assert r.actual_verdict == "BLOCKED", f"{r.scenario_id} not BLOCKED"
            assert r.actual_blocked is True

    def test_safe_scenario_is_pass(self):
        results = evaluate_readonly_scenario_catalog()
        safe = [r for r in results if r.scenario_id == "safe_summary_read"]
        assert len(safe) == 1
        assert safe[0].actual_verdict == "PASS"
        assert safe[0].actual_blocked is False

    def test_all_ok_true_for_expected_scenarios(self):
        """Default catalog: all scenarios match expected_verdict."""
        results = evaluate_readonly_scenario_catalog()
        for r in results:
            assert r.ok is True, f"{r.scenario_id} mismatch: {r.actual_verdict} != {r.expected_verdict}"


class TestMismatch:
    """Mismatch gives ok=False."""

    def test_mismatch_on_modified_scenario(self):
        from core.runtime_governance_readonly_scenario_catalog import (
            RuntimeGovernanceReadOnlyScenario,
        )

        # safe kind but expected BLOCKED -> mismatch
        bad = RuntimeGovernanceReadOnlyScenario(
            scenario_id="test_mismatch",
            description="test",
            permission_envelope_kind="account_summary_read",
            expected_verdict="BLOCKED",
            expected_blocked=True,
            tags=[],
        )
        r = evaluate_readonly_scenario(bad)
        assert r.actual_verdict == "PASS"
        assert r.ok is False


class TestDeterministic:
    """Same result twice."""

    def test_deterministic_output(self):
        r1 = evaluate_readonly_scenario_catalog()
        r2 = evaluate_readonly_scenario_catalog()
        assert readonly_evaluations_to_dict(r1) == readonly_evaluations_to_dict(r2)


class TestSerialization:
    """to_dict and to_markdown."""

    def test_to_dict_returns_list_of_dicts(self):
        results = evaluate_readonly_scenario_catalog()
        dicts = readonly_evaluations_to_dict(results)
        assert isinstance(dicts, list)
        assert len(dicts) == 6
        for d in dicts:
            assert isinstance(d, dict)
            assert "scenario_id" in d
            assert "ok" in d
            assert "notes" in d

    def test_markdown_contains_header(self):
        results = evaluate_readonly_scenario_catalog()
        md = readonly_evaluations_to_markdown(results)
        assert "# Read-Only Scenario Evaluations" in md
        assert "| scenario_id |" in md

    def test_markdown_contains_all_scenarios(self):
        results = evaluate_readonly_scenario_catalog()
        md = readonly_evaluations_to_markdown(results)
        assert "safe_summary_read" in md
        assert "unsafe_network" in md
        assert "unsafe_write" in md
        assert "unsafe_order" in md
        assert "unsafe_secret" in md
        assert "unsafe_account_mutation" in md
