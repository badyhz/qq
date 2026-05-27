from __future__ import annotations

import pytest

from core.dirty_workspace_duplicate_record import (
    DirtyWorkspaceDuplicateRecord,
    build_duplicate_record,
)


class TestDirtyWorkspaceDuplicate:
    def test_build_record(self) -> None:
        r = build_duplicate_record("orig.py", "copy.py", "SCRIPT", "REMOVE_DUPLICATE")
        assert r.canonical_path == "orig.py"
        assert r.duplicate_path == "copy.py"

    def test_frozen(self) -> None:
        r = build_duplicate_record("a", "b", "C", "D")
        with pytest.raises(AttributeError):
            r.canonical_path = "x"  # type: ignore[misc]

    def test_to_dict_keys(self) -> None:
        r = build_duplicate_record("a", "b", "CONFIG", "KEEP_CANONICAL")
        d = r.to_dict()
        assert set(d.keys()) == {"canonical_path", "duplicate_path", "category", "action"}

    def test_category_preserved(self) -> None:
        r = build_duplicate_record("a", "b", "CREDENTIAL", "QUARANTINE")
        assert r.category == "CREDENTIAL"

    def test_action_preserved(self) -> None:
        r = build_duplicate_record("a", "b", "X", "MERGE")
        assert r.action == "MERGE"

    def test_to_dict_values(self) -> None:
        r = build_duplicate_record("orig.py", "dup.py", "SCRIPT", "REMOVE")
        d = r.to_dict()
        assert d["canonical_path"] == "orig.py"
        assert d["duplicate_path"] == "dup.py"
        assert d["category"] == "SCRIPT"
        assert d["action"] == "REMOVE"
