"""Tests for runtime governance audit event model."""

from __future__ import annotations

import pytest

from core.governance_failure_taxonomy import (
    FailureCategory,
    FailureSeverity,
    GovernanceFailure,
)
from core.runtime_governance_audit_event import (
    RuntimeGovernanceAuditEvent,
    audit_event_to_dict,
    audit_event_to_markdown,
    build_runtime_governance_audit_event,
)


# ── fixtures ──────────────────────────────────────────────────────────

def _make_failure(
    category: FailureCategory = FailureCategory.TIMEOUT,
    severity: FailureSeverity = FailureSeverity.WARNING,
) -> GovernanceFailure:
    return GovernanceFailure(
        category=category,
        severity=severity,
        code="TEST_001",
        message="test failure",
        source="test",
    )


def _base_kwargs(**overrides):
    defaults = dict(
        run_id="run-001",
        adapter_id="adapter-A",
        action="submit_order",
        verdict="blocked",
        failures=None,
        metadata=None,
    )
    defaults.update(overrides)
    return defaults


# ── deterministic event_id ────────────────────────────────────────────


class TestEventIdDeterminism:
    def test_repeated_calls_identical(self):
        """Same inputs always produce same event_id."""
        kw = _base_kwargs()
        e1 = build_runtime_governance_audit_event(**kw)
        e2 = build_runtime_governance_audit_event(**kw)
        assert e1.event_id == e2.event_id

    def test_event_id_changes_on_verdict(self):
        """Different verdict -> different event_id."""
        e1 = build_runtime_governance_audit_event(**_base_kwargs(verdict="blocked"))
        e2 = build_runtime_governance_audit_event(**_base_kwargs(verdict="allowed"))
        assert e1.event_id != e2.event_id

    def test_event_id_changes_on_run_id(self):
        e1 = build_runtime_governance_audit_event(**_base_kwargs(run_id="r1"))
        e2 = build_runtime_governance_audit_event(**_base_kwargs(run_id="r2"))
        assert e1.event_id != e2.event_id

    def test_event_id_changes_on_adapter_id(self):
        e1 = build_runtime_governance_audit_event(**_base_kwargs(adapter_id="a1"))
        e2 = build_runtime_governance_audit_event(**_base_kwargs(adapter_id="a2"))
        assert e1.event_id != e2.event_id

    def test_event_id_changes_on_action(self):
        e1 = build_runtime_governance_audit_event(**_base_kwargs(action="submit"))
        e2 = build_runtime_governance_audit_event(**_base_kwargs(action="cancel"))
        assert e1.event_id != e2.event_id

    def test_event_id_changes_on_failure_categories(self):
        f1 = [_make_failure(FailureCategory.TIMEOUT)]
        f2 = [_make_failure(FailureCategory.RATE_LIMIT)]
        e1 = build_runtime_governance_audit_event(**_base_kwargs(failures=f1))
        e2 = build_runtime_governance_audit_event(**_base_kwargs(failures=f2))
        assert e1.event_id != e2.event_id

    def test_event_id_is_hex_string(self):
        e = build_runtime_governance_audit_event(**_base_kwargs())
        assert len(e.event_id) == 16
        int(e.event_id, 16)  # valid hex


# ── categories / severities sorted ────────────────────────────────────


class TestSortedCollections:
    def test_categories_sorted(self):
        failures = [
            _make_failure(FailureCategory.UNKNOWN),
            _make_failure(FailureCategory.ADAPTER_FAILURE),
            _make_failure(FailureCategory.POLICY_BLOCK),
        ]
        e = build_runtime_governance_audit_event(**_base_kwargs(failures=failures))
        assert e.categories == sorted(e.categories)

    def test_severities_sorted(self):
        failures = [
            _make_failure(severity=FailureSeverity.CRITICAL),
            _make_failure(severity=FailureSeverity.INFO),
            _make_failure(severity=FailureSeverity.WARNING),
        ]
        e = build_runtime_governance_audit_event(**_base_kwargs(failures=failures))
        assert e.severities == sorted(e.severities)

    def test_empty_failures(self):
        e = build_runtime_governance_audit_event(**_base_kwargs(failures=[]))
        assert e.failure_count == 0
        assert e.categories == []
        assert e.severities == []

    def test_none_failures(self):
        e = build_runtime_governance_audit_event(**_base_kwargs(failures=None))
        assert e.failure_count == 0
        assert e.categories == []

    def test_mixed_failures_deduplicated(self):
        """Duplicate category+severity pairs deduplicated via set."""
        failures = [
            _make_failure(FailureCategory.TIMEOUT, FailureSeverity.WARNING),
            _make_failure(FailureCategory.TIMEOUT, FailureSeverity.WARNING),
        ]
        e = build_runtime_governance_audit_event(**_base_kwargs(failures=failures))
        assert e.failure_count == 2
        assert len(e.categories) == 1
        assert len(e.severities) == 1


# ── dict serialization ────────────────────────────────────────────────


class TestDictSerialization:
    def test_roundtrip_keys(self):
        e = build_runtime_governance_audit_event(**_base_kwargs())
        d = audit_event_to_dict(e)
        expected_keys = {
            "event_id", "run_id", "adapter_id", "action", "verdict",
            "failure_count", "categories", "severities", "metadata",
        }
        assert set(d.keys()) == expected_keys

    def test_values_match(self):
        kw = _base_kwargs(metadata={"k": "v"})
        e = build_runtime_governance_audit_event(**kw)
        d = audit_event_to_dict(e)
        assert d["run_id"] == "run-001"
        assert d["adapter_id"] == "adapter-A"
        assert d["action"] == "submit_order"
        assert d["verdict"] == "blocked"
        assert d["metadata"] == {"k": "v"}

    def test_dict_is_copy(self):
        e = build_runtime_governance_audit_event(**_base_kwargs(metadata={"k": "v"}))
        d = audit_event_to_dict(e)
        d["metadata"]["k"] = "mutated"
        assert e.metadata["k"] == "v"


# ── markdown deterministic ────────────────────────────────────────────


class TestMarkdownDeterminism:
    def test_repeated_calls_identical(self):
        kw = _base_kwargs()
        e = build_runtime_governance_audit_event(**kw)
        m1 = audit_event_to_markdown(e)
        m2 = audit_event_to_markdown(e)
        assert m1 == m2

    def test_contains_expected_fields(self):
        e = build_runtime_governance_audit_event(**_base_kwargs())
        md = audit_event_to_markdown(e)
        assert "run_id" in md
        assert "adapter_id" in md
        assert "action" in md
        assert "verdict" in md
        assert "failure_count" in md
        assert "categories" in md
        assert "severities" in md

    def test_empty_failures_shows_none(self):
        e = build_runtime_governance_audit_event(**_base_kwargs(failures=[]))
        md = audit_event_to_markdown(e)
        assert "(none)" in md

    def test_metadata_sorted_by_key(self):
        e = build_runtime_governance_audit_event(
            **_base_kwargs(metadata={"z": 1, "a": 2, "m": 3})
        )
        md = audit_event_to_markdown(e)
        pos_a = md.index("**a:**")
        pos_m = md.index("**m:**")
        pos_z = md.index("**z:**")
        assert pos_a < pos_m < pos_z

    def test_no_timestamp_in_output(self):
        e = build_runtime_governance_audit_event(**_base_kwargs())
        md = audit_event_to_markdown(e)
        # no ISO date pattern
        import re
        assert not re.search(r"\d{4}-\d{2}-\d{2}", md)
