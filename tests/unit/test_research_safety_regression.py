"""Tests for research safety regression — T5231-T5240.

Dirty workspace, frozen file, git-add-dot, import scan tests.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from core.research_safety_regression import (
    check_safety_flags, scan_forbidden_imports, check_frozen_files,
    build_safety_report, safety_report_to_dict, FROZEN_PATTERNS,
)


class TestSafetyRegressionNormal:
    def test_safety_flags_default(self):
        valid, errors = check_safety_flags()
        assert valid is True
        assert errors == ()

    def test_build_report_default(self):
        r = build_safety_report()
        assert r.verdict == "PASS"
        assert r.release_hold == "HOLD"
        assert r.advisory_only is True

    def test_report_to_dict(self):
        r = build_safety_report()
        d = safety_report_to_dict(d if isinstance(r, dict) else r)
        assert d["release_hold"] == "HOLD"


class TestSafetyRegressionEdge:
    def test_workspace_dirty_partial(self):
        r = build_safety_report(workspace_dirty=True)
        assert r.verdict == "PARTIAL"

    def test_no_violations_clean(self):
        r = build_safety_report()
        assert r.frozen_files_touched == ()
        assert r.forbidden_imports_found == ()


class TestSafetyRegressionAdversarial:
    def test_non_hold_fails(self):
        r = build_safety_report(release_hold="BAD")
        assert r.verdict == "FAIL"

    def test_non_advisory_fails(self):
        r = build_safety_report(advisory_only=False)
        assert r.verdict == "FAIL"

    def test_non_human_review_fails(self):
        r = build_safety_report(human_review_required=False)
        assert r.verdict == "FAIL"

    def test_git_add_dot_fails(self):
        r = build_safety_report(git_add_dot=True)
        assert r.verdict == "FAIL"

    def test_frozen_file_violation(self):
        r = build_safety_report(touched_files=("core/live_runner.py",))
        assert r.verdict == "FAIL"
        assert len(r.frozen_files_touched) > 0

    def test_frozen_pattern_match(self):
        violations = check_frozen_files(("PROJECT_STATE.md",))
        assert len(violations) > 0

    def test_clean_file_no_violation(self):
        violations = check_frozen_files(("core/data_feed.py",))
        assert len(violations) == 0


class TestSafetyRegressionDeterministic:
    def test_report_deterministic(self):
        r1 = build_safety_report()
        r2 = build_safety_report()
        assert safety_report_to_dict(r1) == safety_report_to_dict(r2)


class TestSafetyRegressionSafetyBoundary:
    def test_frozen_patterns_cover_critical(self):
        assert "PROJECT_STATE.md" in FROZEN_PATTERNS
        assert "TASKS.md" in FROZEN_PATTERNS

    def test_report_holds_safety(self):
        r = build_safety_report()
        assert r.release_hold == "HOLD"
        assert r.advisory_only is True
        assert r.human_review_required is True
