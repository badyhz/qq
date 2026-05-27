"""Tests for core.runtime_governance_invariant_checker."""

from __future__ import annotations

from core.runtime_governance_contract import RuntimeGovernanceInput
from core.runtime_governance_invariant_checker import (
    RuntimeGovernanceInvariantResult,
    check_runtime_governance_invariants,
    invariants_to_dict,
    invariants_to_markdown,
    summarize_runtime_governance_invariants,
)


def _valid_input(**overrides) -> RuntimeGovernanceInput:
    defaults = dict(
        run_id="r1",
        adapter_id="a1",
        mode="shadow",
        requested_action="scan",
        symbol="BTCUSDT",
        environment="test",
        allow_network=True,
        allow_submit=False,
        allow_file_io=False,
        metadata={},
    )
    defaults.update(overrides)
    return RuntimeGovernanceInput(**defaults)


class TestCheckRuntimeGovernanceInvariants:
    def test_valid_input_all_ok(self):
        results = check_runtime_governance_invariants(_valid_input())
        assert all(r.ok for r in results)
        assert len(results) == 6

    def test_no_submit_outside_test_or_testnet(self):
        inp = _valid_input(allow_submit=True, environment="prod")
        results = check_runtime_governance_invariants(inp)
        r = next(r for r in results if r.invariant_id == "no_submit_outside_test_or_testnet")
        assert not r.ok
        assert r.severity == "error"

    def test_submit_allowed_in_test(self):
        inp = _valid_input(allow_submit=True, environment="test")
        results = check_runtime_governance_invariants(inp)
        r = next(r for r in results if r.invariant_id == "no_submit_outside_test_or_testnet")
        assert r.ok

    def test_submit_allowed_in_testnet(self):
        inp = _valid_input(allow_submit=True, environment="testnet")
        results = check_runtime_governance_invariants(inp)
        r = next(r for r in results if r.invariant_id == "no_submit_outside_test_or_testnet")
        assert r.ok

    def test_no_network_without_explicit_mode(self):
        inp = _valid_input(allow_network=True, mode="")
        results = check_runtime_governance_invariants(inp)
        r = next(r for r in results if r.invariant_id == "no_network_without_explicit_mode")
        assert not r.ok
        assert r.severity == "error"

    def test_mode_must_be_known(self):
        inp = _valid_input(mode="unknown_mode")
        results = check_runtime_governance_invariants(inp)
        r = next(r for r in results if r.invariant_id == "mode_must_be_known")
        assert not r.ok
        assert r.severity == "error"

    def test_adapter_id_required(self):
        inp = _valid_input(adapter_id="")
        results = check_runtime_governance_invariants(inp)
        r = next(r for r in results if r.invariant_id == "adapter_id_required")
        assert not r.ok
        assert r.severity == "error"

    def test_run_id_required(self):
        inp = _valid_input(run_id="")
        results = check_runtime_governance_invariants(inp)
        r = next(r for r in results if r.invariant_id == "run_id_required")
        assert not r.ok
        assert r.severity == "error"

    def test_file_io_default_false_for_shadow(self):
        inp = _valid_input(mode="shadow", allow_file_io=True)
        results = check_runtime_governance_invariants(inp)
        r = next(r for r in results if r.invariant_id == "file_io_default_false_for_shadow")
        assert not r.ok
        assert r.severity == "warning"

    def test_file_io_ok_in_non_shadow(self):
        inp = _valid_input(mode="dry_run", allow_file_io=True)
        results = check_runtime_governance_invariants(inp)
        r = next(r for r in results if r.invariant_id == "file_io_default_false_for_shadow")
        assert r.ok


class TestSummarize:
    def test_summary_counts(self):
        results = check_runtime_governance_invariants(_valid_input())
        s = summarize_runtime_governance_invariants(results)
        assert s["total"] == 6
        assert s["passed"] == 6
        assert s["failed"] == 0
        assert s["errors"] == 0
        assert s["warnings"] == 0
        assert s["all_ok"] is True

    def test_summary_with_failures(self):
        inp = _valid_input(run_id="", adapter_id="", mode="shadow", allow_file_io=True)
        results = check_runtime_governance_invariants(inp)
        s = summarize_runtime_governance_invariants(results)
        assert s["failed"] == 3
        assert s["errors"] == 2
        assert s["warnings"] == 1
        assert s["all_ok"] is False


class TestInvariantsToDict:
    def test_deterministic(self):
        results = check_runtime_governance_invariants(_valid_input())
        d1 = invariants_to_dict(results)
        d2 = invariants_to_dict(results)
        assert d1 == d2

    def test_keys(self):
        results = check_runtime_governance_invariants(_valid_input())
        d = invariants_to_dict(results)
        assert len(d) == 6
        for item in d:
            assert set(item.keys()) == {"ok", "invariant_id", "message", "severity", "metadata"}


class TestInvariantsToMarkdown:
    def test_deterministic(self):
        results = check_runtime_governance_invariants(_valid_input())
        m1 = invariants_to_markdown(results)
        m2 = invariants_to_markdown(results)
        assert m1 == m2

    def test_no_timestamps(self):
        results = check_runtime_governance_invariants(_valid_input())
        md = invariants_to_markdown(results)
        # no ISO timestamps or epoch patterns
        assert "202" not in md or "T" not in md
        assert "UTC" not in md

    def test_contains_table(self):
        results = check_runtime_governance_invariants(_valid_input())
        md = invariants_to_markdown(results)
        assert "| # |" in md
        assert "no_submit_outside_test_or_testnet" in md
