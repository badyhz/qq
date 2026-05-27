"""Tests for runtime_governance_transition_checklist."""

import pytest

from core.runtime_governance_transition_checklist import (
    RuntimeGovernanceChecklistItem,
    build_runtime_governance_transition_checklist,
    summarize_transition_checklist,
    transition_checklist_to_dict,
    transition_checklist_to_markdown,
)


class TestBuildChecklist:
    def test_has_eight_items(self):
        checklist = build_runtime_governance_transition_checklist()
        assert len(checklist) == 8

    def test_all_required(self):
        checklist = build_runtime_governance_transition_checklist()
        assert all(c.required for c in checklist)

    def test_default_all_complete(self):
        checklist = build_runtime_governance_transition_checklist()
        assert all(c.status == "complete" for c in checklist)


class TestVerdict:
    def test_pass_when_all_complete(self):
        checklist = build_runtime_governance_transition_checklist()
        summary = summarize_transition_checklist(checklist)
        assert summary["verdict"] == "PASS"

    def test_fail_when_required_incomplete(self):
        checklist = build_runtime_governance_transition_checklist()
        broken = RuntimeGovernanceChecklistItem(
            item_id=checklist[0].item_id,
            title=checklist[0].title,
            required=True,
            status="incomplete",
            notes="forced",
        )
        modified = [broken] + list(checklist[1:])
        summary = summarize_transition_checklist(modified)
        assert summary["verdict"] == "FAIL"
        assert broken.item_id in summary["incomplete_ids"]


class TestSerialization:
    def test_to_dict_roundtrip(self):
        checklist = build_runtime_governance_transition_checklist()
        dicts = transition_checklist_to_dict(checklist)
        assert len(dicts) == 8
        assert dicts[0]["item_id"] == "contract_stable"

    def test_markdown_deterministic(self):
        checklist = build_runtime_governance_transition_checklist()
        md1 = transition_checklist_to_markdown(checklist)
        md2 = transition_checklist_to_markdown(checklist)
        assert md1 == md2
        assert "[x]" in md1
        assert "Runtime Governance Transition Checklist" in md1
