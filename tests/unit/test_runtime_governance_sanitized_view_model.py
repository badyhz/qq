"""Tests for runtime_governance_sanitized_view_model."""

import pytest

from core.runtime_governance_sanitized_view_model import (
    RuntimeGovernanceSanitizedField,
    RuntimeGovernanceSanitizedView,
    build_runtime_governance_sanitized_view,
    sanitized_view_to_dict,
    sanitized_view_to_markdown,
    summarize_sanitized_view,
)

ALL_VIEW_IDS = ["preflight_summary", "regression_summary", "safety_summary", "artifact_summary"]


class TestForbiddenSensitiveFieldsNotAllowed:
    """Secret fields must have allowed=False."""

    @pytest.mark.parametrize("view_id", ALL_VIEW_IDS)
    def test_no_secret_field_is_allowed(self, view_id: str):
        view = build_runtime_governance_sanitized_view(view_id)
        for f in view.fields:
            if f.sensitivity == "secret":
                assert f.allowed is False, (
                    f"Secret field {f.name!r} in view {view_id!r} must not be allowed"
                )

    def test_secret_field_triggers_policy_check(self):
        """Manually building a view with an allowed secret field should fail validation."""
        bad_view_id = "preflight_summary"
        # Monkey-patch to inject a bad field
        import core.runtime_governance_sanitized_view_model as mod
        original = mod._PREFLIGHT_SUMMARY_FIELDS
        try:
            bad_field = RuntimeGovernanceSanitizedField(
                "leaked_key", "str", "secret", True, "none"
            )
            mod._PREFLIGHT_SUMMARY_FIELDS = original + [bad_field]
            mod._VIEWS["preflight_summary"] = (mod._PREFLIGHT_SUMMARY_FIELDS, "PASS")
            with pytest.raises(ValueError, match="Policy violation.*secret field.*leaked_key"):
                build_runtime_governance_sanitized_view("preflight_summary")
        finally:
            mod._PREFLIGHT_SUMMARY_FIELDS = original
            mod._VIEWS["preflight_summary"] = (original, "PASS")


class TestSummariesDeterministic:
    """Summaries must be identical across repeated calls."""

    @pytest.mark.parametrize("view_id", ALL_VIEW_IDS)
    def test_summary_deterministic(self, view_id: str):
        view = build_runtime_governance_sanitized_view(view_id)
        s1 = summarize_sanitized_view(view)
        s2 = summarize_sanitized_view(view)
        assert s1 == s2

    @pytest.mark.parametrize("view_id", ALL_VIEW_IDS)
    def test_to_dict_deterministic(self, view_id: str):
        view = build_runtime_governance_sanitized_view(view_id)
        d1 = sanitized_view_to_dict(view)
        d2 = sanitized_view_to_dict(view)
        assert d1 == d2


class TestMarkdownDeterministic:
    """Markdown output must be identical across repeated calls."""

    @pytest.mark.parametrize("view_id", ALL_VIEW_IDS)
    def test_markdown_deterministic(self, view_id: str):
        view = build_runtime_governance_sanitized_view(view_id)
        m1 = sanitized_view_to_markdown(view)
        m2 = sanitized_view_to_markdown(view)
        assert m1 == m2
        # Verify it contains the view id
        assert view_id in m1


class TestUnknownViewRaisesValueError:
    """Unknown view id must raise ValueError."""

    def test_unknown_view_id(self):
        with pytest.raises(ValueError, match="Unknown sanitized view id"):
            build_runtime_governance_sanitized_view("nonexistent_view")

    def test_empty_view_id(self):
        with pytest.raises(ValueError, match="Unknown sanitized view id"):
            build_runtime_governance_sanitized_view("")
