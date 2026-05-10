import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_ohlcv_gap_validation_plan_v1 import generate_ohlcv_gap_validation_plan_v1


def test_plan_with_valid_candidates(tmp_path):
    candidates = [
        {
            "record_id": "rec-1",
            "source_row_hash": "hash-1",
            "symbol": "BNBUSDT",
            "timeframe": "1m",
            "timestamp": 1760579200000,
            "open": 580.0,
            "high": 590.0,
            "low": 570.0,
            "close": 585.0,
            "volume": 10000.0,
            "observation_only": True,
            "synthetic_placeholder": False
        },
        {
            "record_id": "rec-2",
            "source_row_hash": "hash-2",
            "symbol": "BNBUSDT",
            "timeframe": "1m",
            "timestamp": 1760579260000,
            "open": 585.0,
            "high": 595.0,
            "low": 575.0,
            "close": 590.0,
            "volume": 12000.0,
            "observation_only": True,
            "synthetic_placeholder": False
        }
    ]
    candidate_result = {
        "valid_for_gap_validation": True,
        "gap_validation_candidates": candidates
    }
    result = generate_ohlcv_gap_validation_plan_v1(candidate_result=candidate_result)

    assert result["plan_ready"] is True
    assert result["planned_validation_count"] == 2
    assert result["valid_for_gap_validation"] is True
    assert len(result["validation_items"]) == 2

    for item in result["validation_items"]:
        assert item["observation_only"] is True
        assert item["dry_run_allowed"] is False
        assert item["validation_type"] == "OHLCV_SAMPLE_GAP_VALIDATION"


def test_candidates_exceed_previous_gap(tmp_path):
    previous_gap = 22
    candidates = []
    for i in range(previous_gap + 5):
        candidates.append({
            "record_id": f"rec-{i}",
            "source_row_hash": f"hash-{i}",
            "symbol": "BNBUSDT",
            "timeframe": "1m",
            "timestamp": 1760579200000 + (i * 60000),
            "open": 580.0 + i,
            "high": 590.0 + i,
            "low": 570.0 + i,
            "close": 585.0 + i,
            "volume": 10000.0 + i,
            "observation_only": True,
            "synthetic_placeholder": False
        })

    candidate_result = {
        "valid_for_gap_validation": True,
        "gap_validation_candidates": candidates
    }
    result = generate_ohlcv_gap_validation_plan_v1(candidate_result=candidate_result)

    assert result["plan_ready"] is True
    assert result["planned_validation_count"] <= previous_gap
    assert len(result["validation_items"]) <= previous_gap


def test_no_candidates(tmp_path):
    candidate_result = {
        "valid_for_gap_validation": False,
        "gap_validation_candidates": []
    }
    result = generate_ohlcv_gap_validation_plan_v1(candidate_result=candidate_result)

    assert result["plan_ready"] is False
    assert result["planned_validation_count"] == 0
    assert len(result["validation_items"]) == 0


def test_dry_run_always_false(tmp_path):
    candidates = [
        {
            "record_id": "rec-1",
            "source_row_hash": "hash-1",
            "symbol": "BNBUSDT",
            "timeframe": "1m",
            "timestamp": 1760579200000,
            "open": 580.0,
            "high": 590.0,
            "low": 570.0,
            "close": 585.0,
            "volume": 10000.0,
            "observation_only": True,
            "synthetic_placeholder": False
        }
    ]
    candidate_result = {
        "valid_for_gap_validation": True,
        "gap_validation_candidates": candidates
    }
    result = generate_ohlcv_gap_validation_plan_v1(candidate_result=candidate_result)

    assert result["valid_for_testnet_dry_run"] is False
    for item in result["validation_items"]:
        assert item["dry_run_allowed"] is False


def test_safety_flags(tmp_path):
    result = generate_ohlcv_gap_validation_plan_v1()
    assert result["allowed_mode"] == "SHADOW_ONLY"
    assert result["collection_mode"] == "SHADOW_COLLECTION"
    assert result["submit_permission"] == "NO_SUBMIT"
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False
    assert result["submit_attempted"] is False
    assert result["cancel_attempted"] is False
    assert result["flatten_attempted"] is False


def test_json_flag_works(tmp_path):
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent.parent.parent / "scripts" / "generate_ohlcv_gap_validation_plan_v1.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T417"
