from __future__ import annotations

import pytest

from core.dirty_workspace_freeze_violation import (
    DirtyWorkspaceFreezeViolation,
    build_violation,
    violation_to_dict,
)


class TestDirtyWorkspaceFreezeViolation:
    def test_build_violation(self) -> None:
        v = build_violation("V1", "a.py", "FROZEN_MODIFY", "CRITICAL", "slot-1")
        assert v.violation_id == "V1"
        assert v.file_path == "a.py"

    def test_frozen(self) -> None:
        v = build_violation("V1", "a.py", "T", "HIGH", "s1")
        with pytest.raises(AttributeError):
            v.violation_id = "X"  # type: ignore[misc]

    def test_violation_to_dict_keys(self) -> None:
        v = build_violation("V2", "b.py", "UNAUTHORIZED_DELETE", "MEDIUM", "slot-2")
        d = violation_to_dict(v)
        assert set(d.keys()) == {
            "violation_id",
            "file_path",
            "violation_type",
            "severity",
            "detected_at_slot",
        }

    def test_severity_values(self) -> None:
        for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            v = build_violation("V", "f", "T", sev, "s")
            assert v.severity == sev

    def test_to_dict_matches_violation_to_dict(self) -> None:
        v = build_violation("V3", "c.py", "MODIFY", "LOW", "slot-3")
        assert v.to_dict() == violation_to_dict(v)

    def test_detected_at_slot_preserved(self) -> None:
        v = build_violation("V4", "d.py", "T", "HIGH", "slot-42")
        assert v.detected_at_slot == "slot-42"
