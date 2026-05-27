"""Tests for T840 — runtime governance read-only transition checklist."""
from core.runtime_governance_readonly_transition_checklist import (
    RuntimeGovernanceReadOnlyChecklistItem,
    build_readonly_transition_checklist,
    readonly_transition_checklist_to_dict,
    readonly_transition_checklist_to_markdown,
    summarize_readonly_transition_checklist,
)


def test_checklist_has_8_items():
    items = build_readonly_transition_checklist()
    assert len(items) == 8


def test_all_items_required():
    items = build_readonly_transition_checklist()
    assert all(item.required for item in items)


def test_all_items_complete():
    items = build_readonly_transition_checklist()
    assert all(item.status == "complete" for item in items)


def test_deterministic():
    a = build_readonly_transition_checklist()
    b = build_readonly_transition_checklist()
    assert a == b
    assert a is not b


def test_frozen_dataclass():
    item = build_readonly_transition_checklist()[0]
    try:
        item.item_id = "changed"  # type: ignore[misc]
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass


def test_to_dict_returns_list_of_dicts():
    items = build_readonly_transition_checklist()
    dicts = readonly_transition_checklist_to_dict(items)
    assert isinstance(dicts, list)
    assert len(dicts) == 8
    assert all(isinstance(d, dict) for d in dicts)
    assert dicts[0]["item_id"] == "permission_envelope_reviewed"


def test_markdown_contains_header():
    items = build_readonly_transition_checklist()
    md = readonly_transition_checklist_to_markdown(items)
    assert "# Runtime Governance Read-Only Transition Checklist" in md
    assert "permission_envelope_reviewed" in md


def test_summarize_totals():
    items = build_readonly_transition_checklist()
    summary = summarize_readonly_transition_checklist(items)
    assert summary["total"] == 8
    assert summary["complete"] == 8
    assert summary["pending"] == 0
    assert summary["required"] == 8
