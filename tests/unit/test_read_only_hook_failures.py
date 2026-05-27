"""Tests for read-only hook failures — pure pytest, no I/O."""
from core.read_only_hook_failures import (
    FAILURE_CATEGORIES,
    HookFailure,
    classify_failure,
    hook_failure_to_dict,
)


class TestFailures:
    def test_classify_permission_denied(self):
        hf = classify_failure("PERMISSION_DENIED", "no write allowed", "t1")
        assert isinstance(hf, HookFailure)
        assert hf.category == "PERMISSION_DENIED"
        assert hf.recoverable is False
        assert hf.task_id == "t1"

    def test_failure_categories(self):
        assert len(FAILURE_CATEGORIES) == 5
        assert "PERMISSION_DENIED" in FAILURE_CATEGORIES
        assert "INVARIANT_VIOLATION" in FAILURE_CATEGORIES
        assert "SANITIZATION_FAILURE" in FAILURE_CATEGORIES
        assert "TIMEOUT" in FAILURE_CATEGORIES
        assert "UNKNOWN" in FAILURE_CATEGORIES

    def test_deterministic(self):
        hf = classify_failure("TIMEOUT", "timed out")
        d1 = hook_failure_to_dict(hf)
        d2 = hook_failure_to_dict(hf)
        assert d1 == d2
