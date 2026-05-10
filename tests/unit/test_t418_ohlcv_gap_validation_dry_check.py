import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.run_ohlcv_gap_validation_dry_check_v1 import run_ohlcv_gap_validation_dry_check_v1


def test_validated_samples_reduce_gap(tmp_path):
    plan_result = {
        "planned_validation_count": 2,
        "validation_items": [
            {
                "validation_id": "v1",
                "record_id": "r1",
                "symbol": "BNBUSDT",
                "timeframe": "1m",
                "timestamp": 1760579200000,
                "validation_type": "OHLCV_SAMPLE_GAP_VALIDATION",
                "observation_only": True,
                "dry_run_allowed": False,
                "reason": "test"
            },
            {
                "validation_id": "v2",
                "record_id": "r2",
                "symbol": "BNBUSDT",
                "timeframe": "1m",
                "timestamp": 1760579260000,
                "validation_type": "OHLCV_SAMPLE_GAP_VALIDATION",
                "observation_only": True,
                "dry_run_allowed": False,
                "reason": "test"
            }
        ]
    }

    result = run_ohlcv_gap_validation_dry_check_v1(plan_result=plan_result)

    assert result["previous_gap"] == 22
    assert result["planned_validation_count"] == 2
    assert result["validated_sample_count"] == 2
    assert result["estimated_gap_after_validation"] == 20
    assert result["gap_delta"] == -2
    assert result["gap_validation_effective"] is True


def test_gap_not_below_zero(tmp_path):
    validation_items = []
    for i in range(30):
        validation_items.append({
            "validation_id": f"v{i}",
            "record_id": f"r{i}",
            "symbol": "BNBUSDT",
            "timeframe": "1m",
            "timestamp": 1760579200000 + (i * 60000),
            "validation_type": "OHLCV_SAMPLE_GAP_VALIDATION",
            "observation_only": True,
            "dry_run_allowed": False,
            "reason": "test"
        })

    plan_result = {
        "planned_validation_count": 30,
        "validation_items": validation_items
    }

    result = run_ohlcv_gap_validation_dry_check_v1(plan_result=plan_result)

    # Verify estimated_gap_after_validation can't be negative (since 22 < 30, it'll be 0)
    assert result["estimated_gap_after_validation"] == 0
    assert result["gap_delta"] == -22


def test_invalid_items_not_counted(tmp_path):
    plan_result = {
        "planned_validation_count": 3,
        "validation_items": [
            {
                "validation_id": "v1",
                "record_id": "r1",
                "symbol": "BNBUSDT",
                "timeframe": "1m",
                "timestamp": 1760579200000,
                "validation_type": "OHLCV_SAMPLE_GAP_VALIDATION",
                "observation_only": True,
                "dry_run_allowed": False,
                "reason": "test"
            },
            {
                "validation_id": "v2",
                "record_id": "r2",
                "symbol": "BNBUSDT",
                "timeframe": "1m",
                "timestamp": 1760579260000,
                "validation_type": "OHLCV_SAMPLE_GAP_VALIDATION",
                "observation_only": False,
                "dry_run_allowed": False,
                "reason": "test"
            },
            {
                "validation_id": "v3",
                "record_id": "r3",
                "symbol": "BNBUSDT",
                "timeframe": "1m",
                "timestamp": 1760579320000,
                "validation_type": "OHLCV_SAMPLE_GAP_VALIDATION",
                "observation_only": True,
                "dry_run_allowed": True,
                "reason": "test"
            }
        ]
    }

    result = run_ohlcv_gap_validation_dry_check_v1(plan_result=plan_result)

    assert result["validated_sample_count"] == 1
    assert result["invalid_sample_count"] == 2


def test_valid_for_testnet_dry_run_always_false(tmp_path):
    plan_result = {
        "planned_validation_count": 5,
        "validation_items": [
            {
                "validation_id": "v1",
                "record_id": "r1",
                "symbol": "BNBUSDT",
                "timeframe": "1m",
                "timestamp": 1760579200000,
                "validation_type": "OHLCV_SAMPLE_GAP_VALIDATION",
                "observation_only": True,
                "dry_run_allowed": False,
                "reason": "test"
            }
        ]
    }

    result = run_ohlcv_gap_validation_dry_check_v1(plan_result=plan_result)
    assert result["valid_for_testnet_dry_run"] is False


def test_still_not_ready_when_gap_gt_zero(tmp_path):
    plan_result = {
        "planned_validation_count": 5,
        "validation_items": [
            {
                "validation_id": "v1",
                "record_id": "r1",
                "symbol": "BNBUSDT",
                "timeframe": "1m",
                "timestamp": 1760579200000,
                "validation_type": "OHLCV_SAMPLE_GAP_VALIDATION",
                "observation_only": True,
                "dry_run_allowed": False,
                "reason": "test"
            }
        ]
    }

    result = run_ohlcv_gap_validation_dry_check_v1(plan_result=plan_result)
    assert result["still_not_ready"] is True


def test_safety_flags(tmp_path):
    result = run_ohlcv_gap_validation_dry_check_v1()
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
        [sys.executable, str(Path(__file__).parent.parent.parent / "scripts" / "run_ohlcv_gap_validation_dry_check_v1.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T418"
