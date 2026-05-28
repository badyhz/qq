"""Tests for offline research experiment validator.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.offline_research_experiment_validator import validate_catalog_strict


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "offline_research_experiment_library"
CATALOG_PATH = FIXTURES / "experiment_catalog.json"
INVALID_DIR = FIXTURES / "invalid"


class TestValidateCatalogStrict:
    def test_valid_catalog_passes(self):
        result = validate_catalog_strict(CATALOG_PATH, release_hold="HOLD", min_experiments=60)
        assert result["valid"] is True
        assert result["total_experiments"] >= 60

    def test_release_hold_mismatch_fails(self):
        result = validate_catalog_strict(CATALOG_PATH, release_hold="RELEASE")
        assert result["valid"] is False
        assert any("release_hold" in e for e in result["errors"])

    def test_insufficient_experiments_fails(self):
        result = validate_catalog_strict(CATALOG_PATH, min_experiments=999)
        assert result["valid"] is False
        assert any("insufficient_experiments" in e for e in result["errors"])

    def test_duplicate_experiment_id_fails(self, tmp_path):
        catalog = json.loads(CATALOG_PATH.read_text())
        catalog["experiments"].append(catalog["experiments"][0].copy())
        p = tmp_path / "dup_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False
        assert any("duplicate_experiment_id" in e for e in result["errors"])

    def test_invalid_experiment_fails(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "missing_safety_flags.json").read_text())
            ]
        }
        p = tmp_path / "invalid_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False

    def test_release_hold_not_hold_experiment_fails(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "release_hold_not_hold.json").read_text())
            ]
        }
        p = tmp_path / "bad_rh_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False

    def test_forbidden_command_fails(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "forbidden_command.json").read_text())
            ]
        }
        p = tmp_path / "bad_cmd_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False

    def test_advisory_only_false_fails(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "advisory_only_false.json").read_text())
            ]
        }
        p = tmp_path / "bad_adv_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False

    def test_human_review_false_fails(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "human_review_false.json").read_text())
            ]
        }
        p = tmp_path / "bad_hr_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False

    def test_forbidden_live_string_fails(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "forbidden_live_string.json").read_text())
            ]
        }
        p = tmp_path / "bad_live_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False

    def test_catalog_load_failure(self, tmp_path):
        p = tmp_path / "nonexistent.json"
        result = validate_catalog_strict(p)
        assert result["valid"] is False
        assert any("catalog_load_failed" in e for e in result["errors"])

    def test_no_network_false_fails(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "no_network_false.json").read_text())
            ]
        }
        p = tmp_path / "bad_nn_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False

    def test_forbidden_cancel_command_fails(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "forbidden_cancel_command.json").read_text())
            ]
        }
        p = tmp_path / "bad_cancel_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False

    def test_forbidden_flatten_command_fails(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "forbidden_flatten_command.json").read_text())
            ]
        }
        p = tmp_path / "bad_flatten_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False

    def test_approval_string_fails(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "approval_string.json").read_text())
            ]
        }
        p = tmp_path / "bad_approval_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False

    def test_empty_strategy_set_fails(self, tmp_path):
        catalog = {
            "experiments": [
                json.loads((INVALID_DIR / "empty_strategy_set.json").read_text())
            ]
        }
        p = tmp_path / "bad_ss_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert result["valid"] is False

    def test_machine_readable_output(self):
        result = validate_catalog_strict(CATALOG_PATH, release_hold="HOLD")
        required_keys = [
            "valid", "errors", "warnings", "total_experiments",
            "valid_experiments", "invalid_experiments", "category_counts",
            "release_hold", "advisory_only", "human_review_required",
            "generated_by", "experiment_library_version", "output_hashes",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"
        assert result["release_hold"] == "HOLD"
        assert result["advisory_only"] is True
        assert result["human_review_required"] is True

    def test_category_counts_present(self):
        result = validate_catalog_strict(CATALOG_PATH, release_hold="HOLD")
        assert isinstance(result["category_counts"], dict)
        assert len(result["category_counts"]) >= 20

    def test_duplicate_label_produces_warning(self, tmp_path):
        catalog = json.loads(CATALOG_PATH.read_text())
        # Create two experiments with same label
        dup = catalog["experiments"][0].copy()
        dup["experiment_id"] = "dup_label_test_999"
        catalog["experiments"].append(dup)
        p = tmp_path / "dup_label_catalog.json"
        p.write_text(json.dumps(catalog))
        result = validate_catalog_strict(p, min_experiments=1)
        assert any("duplicate_label" in w for w in result["warnings"])
