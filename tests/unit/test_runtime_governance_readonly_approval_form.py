"""Tests for runtime governance read-only approval form (T844)."""
from __future__ import annotations

import pytest

from core.runtime_governance_readonly_approval_form import (
    RuntimeGovernanceReadOnlyApprovalForm,
    build_readonly_approval_form,
    readonly_approval_form_to_dict,
    readonly_approval_form_to_markdown,
)


@pytest.fixture
def form() -> RuntimeGovernanceReadOnlyApprovalForm:
    return build_readonly_approval_form()


# --- non-authorizations present (at least 3) ---

def test_non_authorizations_at_least_three(form: RuntimeGovernanceReadOnlyApprovalForm):
    assert len(form.explicit_non_authorizations) >= 3


# --- required checks present ---

def test_required_checks_present(form: RuntimeGovernanceReadOnlyApprovalForm):
    assert len(form.required_checks) > 0
    assert isinstance(form.required_checks, list)


# --- approval statement contains "read-only" ---

def test_approval_statement_contains_readonly(form: RuntimeGovernanceReadOnlyApprovalForm):
    assert "read-only" in form.approval_statement.lower()


# --- deterministic ---

def test_deterministic():
    a = build_readonly_approval_form()
    b = build_readonly_approval_form()
    assert a == b
    assert readonly_approval_form_to_dict(a) == readonly_approval_form_to_dict(b)
    assert readonly_approval_form_to_markdown(a) == readonly_approval_form_to_markdown(b)


# --- to_dict has expected keys ---

def test_to_dict_expected_keys(form: RuntimeGovernanceReadOnlyApprovalForm):
    d = readonly_approval_form_to_dict(form)
    expected = {
        "form_id",
        "required_checks",
        "approval_statement",
        "explicit_non_authorizations",
        "signer_role",
        "notes",
    }
    assert set(d.keys()) == expected


# --- markdown contains non-authorizations ---

def test_markdown_contains_non_authorizations(form: RuntimeGovernanceReadOnlyApprovalForm):
    md = readonly_approval_form_to_markdown(form)
    for na in form.explicit_non_authorizations:
        assert na in md
