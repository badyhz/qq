from __future__ import annotations

import pytest

from core.dirty_workspace_file_record import DirtyWorkspaceFileRecord
from core.dirty_workspace_classification_result import (
    DirtyWorkspaceClassificationResult,
    build_classification_result,
)


class TestDirtyWorkspaceClassification:
    def test_build_from_dicts(self) -> None:
        dicts = [
            {"path": "a.py", "tracked": True, "category": "SCRIPT", "risk_level": "HIGH", "action": "REVIEW", "notes": ""},
            {"path": "b.py", "tracked": False, "category": "CONFIG", "risk_level": "LOW", "action": "OK", "notes": "n"},
        ]
        r = build_classification_result(dicts)
        assert r.total_files == 2
        assert r.high_risk_count == 1
        assert r.low_risk_count == 1
        assert r.medium_risk_count == 0

    def test_frozen_record(self) -> None:
        rec = DirtyWorkspaceFileRecord(
            path="x.py", tracked=True, category="C", risk_level="HIGH", action="A", notes=""
        )
        with pytest.raises(AttributeError):
            rec.path = "y.py"  # type: ignore[misc]

    def test_record_to_dict_keys(self) -> None:
        rec = DirtyWorkspaceFileRecord(
            path="x.py", tracked=True, category="C", risk_level="HIGH", action="A", notes="n"
        )
        d = rec.to_dict()
        assert set(d.keys()) == {"path", "tracked", "category", "risk_level", "action", "notes"}

    def test_high_medium_low_counts(self) -> None:
        dicts = [
            {"path": "a", "risk_level": "HIGH"},
            {"path": "b", "risk_level": "HIGH"},
            {"path": "c", "risk_level": "MEDIUM"},
            {"path": "d", "risk_level": "LOW"},
        ]
        r = build_classification_result(dicts)
        assert r.high_risk_count == 2
        assert r.medium_risk_count == 1
        assert r.low_risk_count == 1

    def test_classification_frozen(self) -> None:
        r = build_classification_result([])
        with pytest.raises(AttributeError):
            r.total_files = 99  # type: ignore[misc]

    def test_empty_classification(self) -> None:
        r = build_classification_result([])
        assert r.total_files == 0
        assert r.records == ()
