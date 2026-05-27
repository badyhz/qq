"""T837 — Tests for runtime governance read-only blocker summary."""

import pytest

from core.runtime_governance_readonly_blocker_summary import (
    RuntimeGovernanceReadOnlyBlockerSummary,
    readonly_blocker_summary_to_dict,
    readonly_blocker_summary_to_markdown,
    summarize_readonly_blockers,
)


# ── helpers ────────────────────────────────────────────────────────────


class _FakeEvaluation:
    """Minimal stand-in for RuntimeGovernanceReadOnlyScenarioEvaluation."""

    def __init__(self, actual_verdict: str):
        self.actual_verdict = actual_verdict


# ── tests ──────────────────────────────────────────────────────────────


class TestSummarizeReadonlyBlockers:
    def test_no_args_defaults_to_proceed(self):
        s = summarize_readonly_blockers()
        assert s.total_blockers == 0
        assert s.dangerous_permission_blockers == 0
        assert s.invariant_blockers == 0
        assert s.recommended_action == "PROCEED"
        assert s.notes == []

    def test_no_blockers_proceed(self):
        evals = [_FakeEvaluation("ALLOWED"), _FakeEvaluation("ALLOWED")]
        inv = {"total": 6, "passed": 6, "failed": 0, "errors": 0, "warnings": 0}
        s = summarize_readonly_blockers(evaluations=evals, invariant_summary=inv)
        assert s.total_blockers == 0
        assert s.recommended_action == "PROCEED"

    def test_dangerous_permission_block(self):
        evals = [_FakeEvaluation("BLOCKED")]
        s = summarize_readonly_blockers(evaluations=evals)
        assert s.dangerous_permission_blockers == 1
        assert s.total_blockers == 1
        assert s.recommended_action == "BLOCK"
        assert "1 dangerous permission blocker(s)" in s.notes

    def test_invariant_failure_block(self):
        inv = {"total": 6, "passed": 4, "failed": 2, "errors": 2, "warnings": 0}
        s = summarize_readonly_blockers(invariant_summary=inv)
        assert s.invariant_blockers == 2
        assert s.total_blockers == 2
        assert s.recommended_action == "BLOCK"
        assert "2 invariant failure(s)" in s.notes

    def test_both_blockers_block(self):
        evals = [_FakeEvaluation("BLOCKED"), _FakeEvaluation("ALLOWED")]
        inv = {"failed": 3}
        s = summarize_readonly_blockers(evaluations=evals, invariant_summary=inv)
        assert s.dangerous_permission_blockers == 1
        assert s.invariant_blockers == 3
        assert s.total_blockers == 4
        assert s.recommended_action == "BLOCK"

    def test_deterministic(self):
        evals = [_FakeEvaluation("BLOCKED")]
        inv = {"failed": 1}
        s1 = summarize_readonly_blockers(evaluations=evals, invariant_summary=inv)
        s2 = summarize_readonly_blockers(evaluations=evals, invariant_summary=inv)
        assert s1 == s2
        assert s1 is not s2


class TestReadonlyBlockerSummaryToDict:
    def test_expected_keys(self):
        s = summarize_readonly_blockers()
        d = readonly_blocker_summary_to_dict(s)
        expected_keys = {
            "total_blockers",
            "dangerous_permission_blockers",
            "invariant_blockers",
            "recommended_action",
            "notes",
        }
        assert set(d.keys()) == expected_keys

    def test_values_match(self):
        evals = [_FakeEvaluation("BLOCKED")]
        inv = {"failed": 1}
        s = summarize_readonly_blockers(evaluations=evals, invariant_summary=inv)
        d = readonly_blocker_summary_to_dict(s)
        assert d["total_blockers"] == 2
        assert d["dangerous_permission_blockers"] == 1
        assert d["invariant_blockers"] == 1
        assert d["recommended_action"] == "BLOCK"
        assert isinstance(d["notes"], list)


class TestReadonlyBlockerSummaryToMarkdown:
    def test_contains_action(self):
        for action in ("PROCEED", "BLOCK"):
            s = RuntimeGovernanceReadOnlyBlockerSummary(
                total_blockers=0,
                dangerous_permission_blockers=0,
                invariant_blockers=0,
                recommended_action=action,
            )
            md = readonly_blocker_summary_to_markdown(s)
            assert action in md

    def test_contains_counts(self):
        s = RuntimeGovernanceReadOnlyBlockerSummary(
            total_blockers=3,
            dangerous_permission_blockers=1,
            invariant_blockers=2,
            recommended_action="BLOCK",
            notes=["1 dangerous permission blocker(s)", "2 invariant failure(s)"],
        )
        md = readonly_blocker_summary_to_markdown(s)
        assert "Total Blockers:** 3" in md
        assert "Dangerous Permission Blockers:** 1" in md
        assert "Invariant Blockers:** 2" in md
        assert "BLOCK" in md

    def test_notes_section_present_when_notes(self):
        s = RuntimeGovernanceReadOnlyBlockerSummary(
            total_blockers=1,
            dangerous_permission_blockers=1,
            invariant_blockers=0,
            recommended_action="BLOCK",
            notes=["note one"],
        )
        md = readonly_blocker_summary_to_markdown(s)
        assert "## Notes" in md
        assert "- note one" in md

    def test_no_notes_section_when_empty(self):
        s = summarize_readonly_blockers()
        md = readonly_blocker_summary_to_markdown(s)
        assert "## Notes" not in md
