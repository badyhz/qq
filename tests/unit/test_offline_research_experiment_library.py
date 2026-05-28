"""Tests for offline research experiment library.

No network. No exchange. No runtime. No planner. Advisory only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.offline_research_experiment_library import (
    FORBIDDEN_COMMANDS,
    FORBIDDEN_LIVE_STRINGS,
    REQUIRED_EXPERIMENT_FIELDS,
    REQUIRED_SAFETY_FLAGS,
    build_experiment_manifest,
    check_forbidden_strings,
    compute_experiment_hash,
    load_experiment_catalog,
    validate_experiment,
    validate_forbidden_commands,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "offline_research_experiment_library"
CATALOG_PATH = FIXTURES / "experiment_catalog.json"
INVALID_DIR = FIXTURES / "invalid"


class TestLoadCatalog:
    def test_valid_catalog_loads(self):
        catalog = load_experiment_catalog(CATALOG_PATH)
        assert "experiments" in catalog
        assert isinstance(catalog["experiments"], list)

    def test_missing_experiments_key(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps({"version": "1.0.0"}))
        with pytest.raises(ValueError, match="missing 'experiments' key"):
            load_experiment_catalog(p)

    def test_experiments_not_list(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps({"experiments": "not_a_list"}))
        with pytest.raises(ValueError, match="must be a list"):
            load_experiment_catalog(p)

    def test_not_json_object(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps([1, 2, 3]))
        with pytest.raises(ValueError, match="must be a JSON object"):
            load_experiment_catalog(p)


class TestValidateExperiment:
    def test_valid_experiment(self):
        catalog = load_experiment_catalog(CATALOG_PATH)
        exp = catalog["experiments"][0]
        errors = validate_experiment(exp)
        assert errors == []

    def test_all_20_experiments_valid(self):
        catalog = load_experiment_catalog(CATALOG_PATH)
        assert len(catalog["experiments"]) >= 20
        for exp in catalog["experiments"]:
            errors = validate_experiment(exp)
            assert errors == [], f"{exp['experiment_id']}: {errors}"

    def test_missing_required_field(self):
        exp = {"experiment_id": "test"}
        errors = validate_experiment(exp)
        assert any("missing_required_field" in e for e in errors)

    def test_missing_safety_flag(self):
        with open(INVALID_DIR / "missing_safety_flags.json") as f:
            exp = json.load(f)
        errors = validate_experiment(exp)
        assert any("missing_safety_flag" in e for e in errors)

    def test_release_hold_not_hold(self):
        with open(INVALID_DIR / "release_hold_not_hold.json") as f:
            exp = json.load(f)
        errors = validate_experiment(exp)
        assert any("release_hold must be HOLD" in e for e in errors)

    def test_advisory_only_false(self):
        with open(INVALID_DIR / "advisory_only_false.json") as f:
            exp = json.load(f)
        errors = validate_experiment(exp)
        assert any("advisory_only must be True" in e for e in errors)

    def test_human_review_required_false(self):
        with open(INVALID_DIR / "human_review_false.json") as f:
            exp = json.load(f)
        errors = validate_experiment(exp)
        assert any("human_review_required must be True" in e for e in errors)

    def test_forbidden_live_string_detected(self):
        with open(INVALID_DIR / "forbidden_live_string.json") as f:
            exp = json.load(f)
        errors = check_forbidden_strings(exp)
        assert len(errors) > 0


class TestForbiddenCommands:
    def test_forbidden_command_in_allowed(self):
        with open(INVALID_DIR / "forbidden_command.json") as f:
            exp = json.load(f)
        errors = validate_forbidden_commands(exp)
        assert any("forbidden_command_in_allowed" in e for e in errors)

    def test_valid_commands_pass(self):
        catalog = load_experiment_catalog(CATALOG_PATH)
        for exp in catalog["experiments"]:
            errors = validate_forbidden_commands(exp)
            assert errors == [], f"{exp['experiment_id']}: {errors}"


class TestExperimentHash:
    def test_deterministic_hash(self):
        catalog = load_experiment_catalog(CATALOG_PATH)
        exp = catalog["experiments"][0]
        h1 = compute_experiment_hash(exp)
        h2 = compute_experiment_hash(exp)
        assert h1 == h2

    def test_different_experiments_different_hashes(self):
        catalog = load_experiment_catalog(CATALOG_PATH)
        exps = catalog["experiments"]
        hashes = [compute_experiment_hash(e) for e in exps]
        assert len(set(hashes)) == len(hashes)


class TestManifest:
    def test_build_manifest(self):
        catalog = load_experiment_catalog(CATALOG_PATH)
        manifest = build_experiment_manifest(catalog["experiments"])
        assert manifest["release_hold"] == "HOLD"
        assert manifest["advisory_only"] is True
        assert manifest["human_review_required"] is True
        assert manifest["count"] >= 20

    def test_manifest_entries_have_hashes(self):
        catalog = load_experiment_catalog(CATALOG_PATH)
        manifest = build_experiment_manifest(catalog["experiments"])
        for entry in manifest["entries"]:
            assert "hash" in entry
            assert len(entry["hash"]) == 64  # SHA256 hex


class TestNoNetworkImports:
    def test_no_forbidden_imports_in_library(self):
        module_path = Path(__file__).resolve().parent.parent.parent / "core" / "offline_research_experiment_library.py"
        text = module_path.read_text()
        for forbidden in ["requests", "httpx", "aiohttp", "websocket", "binance", "ccxt"]:
            assert forbidden not in text.lower().split("import"), f"forbidden import: {forbidden}"

    def test_no_forbidden_imports_in_catalog(self):
        module_path = Path(__file__).resolve().parent.parent.parent / "core" / "offline_research_experiment_catalog.py"
        text = module_path.read_text()
        for forbidden in ["requests", "httpx", "aiohttp", "websocket", "binance", "ccxt"]:
            assert forbidden not in text.lower().split("import"), f"forbidden import: {forbidden}"

    def test_no_forbidden_imports_in_validator(self):
        module_path = Path(__file__).resolve().parent.parent.parent / "core" / "offline_research_experiment_validator.py"
        text = module_path.read_text()
        for forbidden in ["requests", "httpx", "aiohttp", "websocket", "binance", "ccxt"]:
            assert forbidden not in text.lower().split("import"), f"forbidden import: {forbidden}"
