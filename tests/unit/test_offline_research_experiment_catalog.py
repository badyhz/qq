"""Tests for offline research experiment catalog.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.offline_research_experiment_catalog import (
    build_command_preview,
    get_experiment_by_id,
    get_experiment_ids,
    load_and_validate_catalog,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "offline_research_experiment_library"
CATALOG_PATH = FIXTURES / "experiment_catalog.json"
INVALID_DIR = FIXTURES / "invalid"


class TestLoadAndValidateCatalog:
    def test_valid_catalog(self):
        result = load_and_validate_catalog(CATALOG_PATH)
        assert result["valid"] is True
        assert result["total_experiments"] >= 60
        assert result["invalid_experiments"] == 0

    def test_invalid_catalog(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "missing_safety_flags.json").read_text())
            ]
        }
        p = tmp_path / "invalid_catalog.json"
        p.write_text(json.dumps(catalog))
        result = load_and_validate_catalog(p)
        assert result["valid"] is False
        assert result["invalid_experiments"] == 1


class TestGetExperimentIds:
    def test_returns_all_ids(self):
        ids = get_experiment_ids(CATALOG_PATH)
        assert len(ids) >= 60
        assert "baseline_major_5m_15m" in ids
        assert "human_review_focus" in ids

    def test_unique_ids(self):
        ids = get_experiment_ids(CATALOG_PATH)
        assert len(ids) == len(set(ids))


class TestGetExperimentById:
    def test_found(self):
        exp = get_experiment_by_id(CATALOG_PATH, "baseline_major_5m_15m")
        assert exp is not None
        assert exp["experiment_id"] == "baseline_major_5m_15m"

    def test_not_found(self):
        exp = get_experiment_by_id(CATALOG_PATH, "nonexistent_experiment")
        assert exp is None


class TestCommandPreview:
    def test_preview_offline_only(self):
        catalog = json.loads(CATALOG_PATH.read_text())
        exp = catalog["experiments"][0]
        commands = build_command_preview(exp)
        assert len(commands) > 0
        for cmd in commands:
            assert "python3 scripts/" in cmd
            for forbidden in ["submit_order", "cancel_order", "flatten", "live_trading"]:
                assert forbidden not in cmd

    def test_preview_includes_strict(self):
        catalog = json.loads(CATALOG_PATH.read_text())
        exp = catalog["experiments"][0]
        commands = build_command_preview(exp)
        for cmd in commands[1:]:
            assert "--strict" in cmd
            assert "--release-hold HOLD" in cmd
