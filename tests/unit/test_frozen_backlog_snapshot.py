"""T1609: Tests for FrozenBacklogSnapshot system."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.frozen_backlog_snapshot import FrozenBacklogSnapshot
from core.frozen_backlog_snapshot_manager import (
    create_snapshot,
    dict_to_snapshot,
    read_snapshot,
    snapshot_to_dict,
    write_snapshot,
)
from core.frozen_backlog_snapshot_renderer import render_snapshot_md

SAMPLE_REPORT = {"total": 5, "items": [{"id": 1, "status": "frozen"}, {"id": 2, "status": "frozen"}]}
SAMPLE_VERSION = "1.0.0"
SAMPLE_TS = "2026-05-28T00:00:00Z"
SAMPLE_ID = "snap-001"


def _make_snapshot(**overrides) -> FrozenBacklogSnapshot:
    defaults = dict(
        snapshot_id=SAMPLE_ID,
        report_data=SAMPLE_REPORT,
        created_at_iso=SAMPLE_TS,
        version=SAMPLE_VERSION,
    )
    defaults.update(overrides)
    return FrozenBacklogSnapshot(**defaults)


class TestCreateSnapshot:
    def test_create_from_report_data(self):
        s = create_snapshot(SAMPLE_REPORT, SAMPLE_VERSION, SAMPLE_TS, SAMPLE_ID)
        assert s.snapshot_id == SAMPLE_ID
        assert s.report_data == SAMPLE_REPORT
        assert s.created_at_iso == SAMPLE_TS
        assert s.version == SAMPLE_VERSION

    def test_create_with_default_id(self):
        s = create_snapshot(SAMPLE_REPORT, SAMPLE_VERSION, SAMPLE_TS)
        assert s.snapshot_id == ""


class TestImmutability:
    def test_frozen_dataclass_rejects_mutation(self):
        s = _make_snapshot()
        with pytest.raises(AttributeError):
            s.snapshot_id = "other"  # type: ignore[misc]

    def test_report_data_dict_not_shared(self):
        """Frozen dataclass holds a reference; caller should not mutate externally."""
        s1 = _make_snapshot()
        s2 = _make_snapshot()
        assert s1.report_data is s2.report_data  # same ref since frozen wrapper


class TestDictRoundTrip:
    def test_snapshot_to_dict_keys(self):
        d = snapshot_to_dict(_make_snapshot())
        assert set(d.keys()) == {"snapshot_id", "report_data", "created_at_iso", "version"}

    def test_round_trip_preserves_data(self):
        original = _make_snapshot()
        d = snapshot_to_dict(original)
        restored = dict_to_snapshot(d)
        assert restored == original

    def test_round_trip_nested_report(self):
        report = {"a": {"b": [1, 2, 3]}, "c": None}
        s = create_snapshot(report, "2.0", SAMPLE_TS, "r1")
        assert dict_to_snapshot(snapshot_to_dict(s)) == s


class TestFileIO:
    def test_write_and_read_back(self, tmp_path: Path):
        s = _make_snapshot()
        p = str(tmp_path / "snap.json")
        write_snapshot(s, p)
        loaded = read_snapshot(p)
        assert loaded == s

    def test_deterministic_json_output(self, tmp_path: Path):
        """Same input produces identical JSON bytes."""
        s = _make_snapshot()
        p1 = str(tmp_path / "a.json")
        p2 = str(tmp_path / "b.json")
        write_snapshot(s, p1)
        write_snapshot(s, p2)
        assert Path(p1).read_bytes() == Path(p2).read_bytes()

    def test_json_uses_sorted_keys(self, tmp_path: Path):
        s = _make_snapshot()
        p = str(tmp_path / "snap.json")
        write_snapshot(s, p)
        raw = Path(p).read_text()
        parsed = json.loads(raw)
        keys = list(parsed.keys())
        assert keys == sorted(keys)


class TestRenderer:
    def test_render_contains_fields(self):
        md = render_snapshot_md(_make_snapshot())
        assert SAMPLE_ID in md
        assert SAMPLE_VERSION in md
        assert SAMPLE_TS in md
        assert "```json" in md

    def test_render_includes_report_json(self):
        md = render_snapshot_md(_make_snapshot())
        assert '"total": 5' in md
