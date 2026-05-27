"""Tests for read-only hook review and rollout — pure pytest, no I/O."""
from core.read_only_hook_review import (
    ReviewChecklist,
    build_default_review_checklist,
    review_checklist_to_dict,
)
from core.read_only_hook_rollout import (
    RolloutHold,
    RollbackStep,
    build_rollback_plan,
    build_rollout_hold,
    rollout_hold_to_dict,
    rollback_step_to_dict,
)


class TestReview:
    def test_default_checklist(self):
        rc = build_default_review_checklist()
        assert isinstance(rc, ReviewChecklist)
        assert len(rc.items) == 10
        assert rc.all_checked is False
        assert rc.verdict == "PENDING"

    def test_all_checked_verdict(self):
        """All checked items should map to APPROVED semantics."""
        rc = build_default_review_checklist()
        assert all(not item.checked for item in rc.items)
        # when all checked, verdict should be APPROVED
        from core.read_only_hook_review import ReviewChecklistItem

        checked_items = [
            ReviewChecklistItem(item.item_id, item.description, True, "")
            for item in rc.items
        ]
        approved = ReviewChecklist(
            checklist_id=rc.checklist_id,
            items=checked_items,
            all_checked=True,
            verdict="APPROVED",
        )
        assert approved.all_checked is True
        assert approved.verdict == "APPROVED"


class TestRollout:
    def test_hold_active(self):
        hold = build_rollout_hold()
        assert isinstance(hold, RolloutHold)
        assert hold.hold_active is True
        assert hold.final_verdict == "HOLD"

    def test_rollback_plan(self):
        steps = build_rollback_plan()
        assert len(steps) == 5
        assert all(isinstance(s, RollbackStep) for s in steps)
        assert all(s.reversible for s in steps)
        # ordered 1-5
        orders = [s.order for s in steps]
        assert orders == [1, 2, 3, 4, 5]

    def test_deterministic(self):
        hold = build_rollout_hold()
        d1 = rollout_hold_to_dict(hold)
        d2 = rollout_hold_to_dict(hold)
        assert d1 == d2
        steps = build_rollback_plan()
        s1 = [rollback_step_to_dict(s) for s in steps]
        s2 = [rollback_step_to_dict(s) for s in steps]
        assert s1 == s2
