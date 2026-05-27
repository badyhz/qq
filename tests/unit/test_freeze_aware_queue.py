from __future__ import annotations

import pytest

from core.freeze_aware_queue import FreezeAwareQueue
from core.freeze_aware_task_state import FreezeAwareTaskState


class TestFreezeAwareQueue:
    def test_create_queue(self) -> None:
        q = FreezeAwareQueue(
            queue_id="Q1",
            tasks=("t1", "t2"),
            frozen_files=("f1",),
            release_hold=False,
        )
        assert q.queue_id == "Q1"
        assert q.tasks == ("t1", "t2")

    def test_frozen(self) -> None:
        q = FreezeAwareQueue(queue_id="Q2", tasks=(), frozen_files=(), release_hold=True)
        with pytest.raises(AttributeError):
            q.queue_id = "X"  # type: ignore[misc]

    def test_release_hold(self) -> None:
        q = FreezeAwareQueue(queue_id="Q", tasks=(), frozen_files=(), release_hold=True)
        assert q.release_hold is True

    def test_frozen_files_tuple(self) -> None:
        ff = ("a.py", "b.py")
        q = FreezeAwareQueue(queue_id="Q", tasks=(), frozen_files=ff, release_hold=False)
        assert q.frozen_files == ff


class TestFreezeAwareTaskState:
    def test_state_values(self) -> None:
        ts = FreezeAwareTaskState()
        assert ts.NOT_STARTED == "NOT_STARTED"
        assert ts.IN_PROGRESS == "IN_PROGRESS"
        assert ts.COMPLETED == "COMPLETED"
        assert ts.HUMAN_REVIEW_REQUIRED == "HUMAN_REVIEW_REQUIRED"
        assert ts.BLOCKED == "BLOCKED"
        assert ts.PARTIAL == "PARTIAL"
        assert ts.PASS == "PASS"
        assert ts.DENIED == "DENIED"

    def test_validate_state_valid(self) -> None:
        ts = FreezeAwareTaskState()
        for s in ("NOT_STARTED", "IN_PROGRESS", "COMPLETED", "BLOCKED", "PARTIAL", "PASS", "DENIED", "HUMAN_REVIEW_REQUIRED"):
            assert ts.validate_state(s) is True

    def test_validate_state_invalid(self) -> None:
        ts = FreezeAwareTaskState()
        assert ts.validate_state("BOGUS") is False
        assert ts.validate_state("") is False
        assert ts.validate_state("not_started") is False
