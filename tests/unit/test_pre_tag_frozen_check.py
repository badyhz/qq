"""Tests for pre-tag frozen boundary check."""
from __future__ import annotations

from core.workflow_safety import pre_tag_frozen_check, FROZEN_PATTERNS


def test_clean_files_pass():
    result = pre_tag_frozen_check(["core/workflow_runtime.py", "tests/test_foo.py"])
    assert result["safe"]
    assert result["violations"] == []
    assert result["checked"] == 2


def test_frozen_file_detected():
    result = pre_tag_frozen_check(["core/live_runner.py"])
    assert not result["safe"]
    assert len(result["violations"]) == 1
    assert result["violations"][0]["file"] == "core/live_runner.py"


def test_multiple_frozen_files():
    result = pre_tag_frozen_check([
        "core/live_runner.py",
        "scripts/safe_flatten_testnet_symbol.py",
        "core/workflow_runtime.py",
    ])
    assert not result["safe"]
    assert len(result["violations"]) == 2


def test_empty_list():
    result = pre_tag_frozen_check([])
    assert result["safe"]
    assert result["checked"] == 0


def test_frozen_pattern_coverage():
    for pattern in FROZEN_PATTERNS:
        result = pre_tag_frozen_check([f"some/path/{pattern}_file.py"])
        assert not result["safe"], f"Pattern '{pattern}' not detected"


def test_partial_pattern_match():
    result = pre_tag_frozen_check(["scripts/run_shadow_observation_experiments.py"])
    assert not result["safe"]


def test_no_false_positives():
    result = pre_tag_frozen_check([
        "core/shadow_copy.py",
        "scripts/runner.py",
        "docs/frozen_doc.md",
    ])
    assert result["safe"]
