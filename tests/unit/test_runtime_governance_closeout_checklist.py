"""Tests for runtime_governance_closeout_checklist."""

import pytest

from core.runtime_governance_closeout_checklist import (
    RuntimeGovernanceCloseoutItem,
    build_runtime_governance_closeout_checklist,
    closeout_checklist_to_dict,
    closeout_checklist_to_markdown,
    summarize_closeout_checklist,
)


class TestDataclass:
    def test_frozen(self):
        item = RuntimeGovernanceCloseoutItem(
            item_id="x", description="d", status="complete",
            required=True, evidence="e",
        )
        with pytest.raises(AttributeError):
            item.item_id = "y"  # type: ignore[misc]

    def test_fields(self):
        item = RuntimeGovernanceCloseoutItem(
            item_id="x", description="d", status="incomplete",
            required=False, evidence="ev",
        )
        assert item.item_id == "x"
        assert item.description == "d"
        assert item.status == "incomplete"
        assert item.required is False
        assert item.evidence == "ev"


class TestBuildChecklist:
    def test_count(self):
        cl = build_runtime_governance_closeout_checklist()
        assert len(cl) == 6

    def test_all_required(self):
        cl = build_runtime_governance_closeout_checklist()
        assert all(c.required for c in cl)

    def test_all_complete(self):
        cl = build_runtime_governance_closeout_checklist()
        assert all(c.status == "complete" for c in cl)

    def test_item_ids(self):
        cl = build_runtime_governance_closeout_checklist()
        ids = [c.item_id for c in cl]
        assert ids == [
            "tests_pass",
            "no_submit_evidence",
            "docs_present",
            "frozen_boundaries",
            "future_tasks_hold",
            "no_runtime_integration",
        ]

    def test_descriptions(self):
        cl = build_runtime_governance_closeout_checklist()
        descs = [c.description for c in cl]
        assert "All runtime governance tests pass" in descs[0]
        assert "No-submit evidence verified" in descs[1]
        assert "All module docs present" in descs[2]
        assert "Frozen boundaries documented" in descs[3]
        assert "High-risk future tasks marked HOLD" in descs[4]
        assert "No runtime integration performed" in descs[5]


class TestToDict:
    def test_length(self):
        cl = build_runtime_governance_closeout_checklist()
        d = closeout_checklist_to_dict(cl)
        assert len(d) == 6

    def test_keys(self):
        cl = build_runtime_governance_closeout_checklist()
        d = closeout_checklist_to_dict(cl)
        expected_keys = {"item_id", "description", "status", "required", "evidence"}
        for row in d:
            assert set(row.keys()) == expected_keys

    def test_values_match(self):
        cl = build_runtime_governance_closeout_checklist()
        d = closeout_checklist_to_dict(cl)
        assert d[0]["item_id"] == "tests_pass"
        assert d[0]["status"] == "complete"
        assert d[0]["required"] is True


class TestToMarkdown:
    def test_header(self):
        cl = build_runtime_governance_closeout_checklist()
        md = closeout_checklist_to_markdown(cl)
        assert "# Runtime Governance Closeout Checklist" in md

    def test_table_rows(self):
        cl = build_runtime_governance_closeout_checklist()
        md = closeout_checklist_to_markdown(cl)
        assert "| 1 | tests_pass |" in md
        assert "| 6 | no_runtime_integration |" in md

    def test_checkmarks(self):
        cl = build_runtime_governance_closeout_checklist()
        md = closeout_checklist_to_markdown(cl)
        assert md.count("[x]") == 6
        assert "[ ]" not in md


class TestSummarize:
    def test_pass_verdict(self):
        cl = build_runtime_governance_closeout_checklist()
        s = summarize_closeout_checklist(cl)
        assert s["verdict"] == "PASS"
        assert s["total"] == 6
        assert s["required_count"] == 6
        assert s["complete_count"] == 6
        assert s["incomplete_count"] == 0
        assert s["incomplete_ids"] == []

    def test_fail_when_incomplete(self):
        cl = build_runtime_governance_closeout_checklist()
        # make one incomplete
        broken = RuntimeGovernanceCloseoutItem(
            item_id=cl[0].item_id,
            description=cl[0].description,
            status="incomplete",
            required=cl[0].required,
            evidence=cl[0].evidence,
        )
        cl2 = [broken] + list(cl[1:])
        s = summarize_closeout_checklist(cl2)
        assert s["verdict"] == "FAIL"
        assert s["incomplete_count"] == 1
        assert "tests_pass" in s["incomplete_ids"]

    def test_fail_when_required_incomplete(self):
        cl = build_runtime_governance_closeout_checklist()
        # make one required incomplete
        broken = RuntimeGovernanceCloseoutItem(
            item_id=cl[2].item_id,
            description=cl[2].description,
            status="incomplete",
            required=True,
            evidence="",
        )
        cl2 = list(cl[:2]) + [broken] + list(cl[3:])
        s = summarize_closeout_checklist(cl2)
        assert s["verdict"] == "FAIL"
        assert s["complete_count"] == 5
        assert "docs_present" in s["incomplete_ids"]
