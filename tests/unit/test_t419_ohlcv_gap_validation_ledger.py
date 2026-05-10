import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.update_ohlcv_gap_validation_ledger_v1 import update_ohlcv_gap_validation_ledger_v1


def test_first_write(tmp_path):
    ledger_file = tmp_path / "ledger.json"

    validation_items = [
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

    dry_check_result = {
        "task_id": "T418",
        "validated_sample_count": 2,
        "validation_items": validation_items
    }

    result = update_ohlcv_gap_validation_ledger_v1(
        dry_check_result=dry_check_result,
        ledger_path=str(ledger_file)
    )

    assert result["ledger_updated"] is True
    assert result["previous_ledger_runs"] == 0
    assert result["ledger_runs_after"] == 1
    assert result["new_validated_samples_added"] == 2


def test_idempotent_repeat(tmp_path):
    ledger_file = tmp_path / "ledger.json"

    validation_items = [
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

    dry_check_result = {
        "task_id": "T418",
        "validated_sample_count": 1,
        "validation_items": validation_items
    }

    # First run
    result1 = update_ohlcv_gap_validation_ledger_v1(
        dry_check_result=dry_check_result,
        ledger_path=str(ledger_file)
    )

    # Second run (same dry_check)
    result2 = update_ohlcv_gap_validation_ledger_v1(
        dry_check_result=dry_check_result,
        ledger_path=str(ledger_file)
    )

    assert result2["ledger_updated"] is False
    assert result2["ledger_runs_after"] == 1
    assert result2["idempotency_ok"] is True
    assert result2["duplicate_samples_skipped"] == 1


def test_duplicate_samples(tmp_path):
    ledger_file = tmp_path / "ledger.json"

    validation_items = [
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

    dry_check_result = {
        "task_id": "T418",
        "validated_sample_count": 2,
        "validation_items": validation_items
    }

    result = update_ohlcv_gap_validation_ledger_v1(
        dry_check_result=dry_check_result,
        ledger_path=str(ledger_file)
    )

    assert result["new_validated_samples_added"] == 1
    assert result["duplicate_samples_skipped"] == 1


def test_empty_dry_check(tmp_path):
    ledger_file = tmp_path / "ledger.json"

    dry_check_result = {
        "task_id": "T418",
        "validated_sample_count": 0,
        "validation_items": []
    }

    result = update_ohlcv_gap_validation_ledger_v1(
        dry_check_result=dry_check_result,
        ledger_path=str(ledger_file)
    )

    assert result["valid_for_testnet_dry_run"] is False
    assert result["ledger_updated"] is False


def test_safety_flags(tmp_path):
    result = update_ohlcv_gap_validation_ledger_v1()
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
        [sys.executable, str(Path(__file__).parent.parent.parent / "scripts" / "update_ohlcv_gap_validation_ledger_v1.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T419"
