"""T832 — Tests for read-only invariant checker."""

import pytest

from core.runtime_governance_permission_envelope import (
    RuntimeGovernancePermissionEnvelope,
)
from core.runtime_governance_readonly_invariant_checker import (
    RuntimeGovernanceReadOnlyInvariant,
    check_readonly_permission_invariants,
    readonly_invariants_to_dict,
    readonly_invariants_to_markdown,
    summarize_readonly_invariants,
)


def _safe_envelope() -> RuntimeGovernancePermissionEnvelope:
    """Read-only safe envelope."""
    return RuntimeGovernancePermissionEnvelope(
        allow_read=True,
        allow_write=False,
        allow_network=False,
        allow_order=False,
        allow_account_mutation=False,
        allow_secret_access=False,
        reason="test:safe",
        verdict="PASS",
    )


def _envelope_with(**overrides) -> RuntimeGovernancePermissionEnvelope:
    """Build envelope with overrides from safe baseline."""
    base = dict(
        allow_read=True,
        allow_write=False,
        allow_network=False,
        allow_order=False,
        allow_account_mutation=False,
        allow_secret_access=False,
        reason="test:override",
        verdict="BLOCKED",
    )
    base.update(overrides)
    return RuntimeGovernancePermissionEnvelope(**base)


class TestCheckReadonlyPermissionInvariants:
    def test_safe_envelope_all_ok(self):
        results = check_readonly_permission_invariants(_safe_envelope())
        assert len(results) == 6
        assert all(r.ok for r in results)

    def test_write_blocked_detected(self):
        env = _envelope_with(allow_write=True)
        results = check_readonly_permission_invariants(env)
        no_write = [r for r in results if r.invariant_id == "no_write"]
        assert len(no_write) == 1
        assert not no_write[0].ok
        assert no_write[0].severity == "error"

    def test_network_blocked_detected(self):
        env = _envelope_with(allow_network=True)
        results = check_readonly_permission_invariants(env)
        no_network = [r for r in results if r.invariant_id == "no_network"]
        assert len(no_network) == 1
        assert not no_network[0].ok
        assert no_network[0].severity == "error"

    def test_order_detected(self):
        env = _envelope_with(allow_order=True)
        results = check_readonly_permission_invariants(env)
        no_order = [r for r in results if r.invariant_id == "no_order"]
        assert len(no_order) == 1
        assert not no_order[0].ok

    def test_account_mutation_detected(self):
        env = _envelope_with(allow_account_mutation=True)
        results = check_readonly_permission_invariants(env)
        am = [r for r in results if r.invariant_id == "no_account_mutation"]
        assert len(am) == 1
        assert not am[0].ok

    def test_secret_access_detected(self):
        env = _envelope_with(allow_secret_access=True)
        results = check_readonly_permission_invariants(env)
        sa = [r for r in results if r.invariant_id == "no_secret_access"]
        assert len(sa) == 1
        assert not sa[0].ok

    def test_read_disabled_detected(self):
        env = _envelope_with(allow_read=False)
        results = check_readonly_permission_invariants(env)
        read = [r for r in results if r.invariant_id == "read_allowed"]
        assert len(read) == 1
        assert not read[0].ok


class TestSummarize:
    def test_summary_deterministic(self):
        results = check_readonly_permission_invariants(_safe_envelope())
        s1 = summarize_readonly_invariants(results)
        s2 = summarize_readonly_invariants(results)
        assert s1 == s2
        assert s1 == {
            "total": 6,
            "passed": 6,
            "failed": 0,
            "errors": 0,
            "warnings": 0,
            "all_ok": True,
        }

    def test_summary_with_failures(self):
        env = _envelope_with(allow_write=True, allow_network=True)
        results = check_readonly_permission_invariants(env)
        s = summarize_readonly_invariants(results)
        assert s["failed"] == 2
        assert s["errors"] == 2
        assert not s["all_ok"]


class TestSerialization:
    def test_to_dict_deterministic(self):
        results = check_readonly_permission_invariants(_safe_envelope())
        d1 = readonly_invariants_to_dict(results)
        d2 = readonly_invariants_to_dict(results)
        assert d1 == d2
        assert len(d1) == 6
        assert all("invariant_id" in d for d in d1)

    def test_markdown_deterministic(self):
        results = check_readonly_permission_invariants(_safe_envelope())
        m1 = readonly_invariants_to_markdown(results)
        m2 = readonly_invariants_to_markdown(results)
        assert m1 == m2
        assert "# Read-Only Invariants" in m1
        assert "Total:" in m1
