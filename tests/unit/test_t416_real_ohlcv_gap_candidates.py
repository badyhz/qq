import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.validate_real_ohlcv_gap_candidates import validate_real_ohlcv_gap_candidates


def test_complete_valid_records(tmp_path):
    records = [
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
    records_result = {"records": records}
    result = validate_real_ohlcv_gap_candidates(records_result=records_result)

    assert result["valid_for_gap_validation"] is True
    assert result["gap_validation_candidate_count"] == 2
    assert result["records_analyzed"] == 2
    assert result["valid_ohlcv_records"] == 2
    assert result["invalid_records"] == 0
    assert result["duplicate_records"] == 0
    assert result["placeholder_records"] == 0
    assert result["fallback_values_detected"] is False
    assert result["timestamp_anomaly_count"] == 0


def test_invalid_placeholder_records(tmp_path):
    records = [
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
            "observation_only": False,
            "synthetic_placeholder": True
        }
    ]
    records_result = {"records": records}
    result = validate_real_ohlcv_gap_candidates(records_result=records_result)

    assert result["valid_for_gap_validation"] is False
    assert result["placeholder_records"] == 1


def test_duplicate_records(tmp_path):
    records = [
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
    records_result = {"records": records}
    result = validate_real_ohlcv_gap_candidates(records_result=records_result)

    assert result["valid_for_gap_validation"] is False
    assert result["duplicate_records"] == 1


def test_invalid_timestamp(tmp_path):
    records = [
        {
            "record_id": "rec-1",
            "source_row_hash": "hash-1",
            "symbol": "BNBUSDT",
            "timeframe": "1m",
            "timestamp": 0,
            "open": 580.0,
            "high": 590.0,
            "low": 570.0,
            "close": 585.0,
            "volume": 10000.0,
            "observation_only": True,
            "synthetic_placeholder": False
        }
    ]
    records_result = {"records": records}
    result = validate_real_ohlcv_gap_candidates(records_result=records_result)

    assert result["valid_for_gap_validation"] is False
    assert result["timestamp_anomaly_count"] == 1


def test_valid_for_testnet_dry_run_always_false(tmp_path):
    records = [
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
    records_result = {"records": records}
    result = validate_real_ohlcv_gap_candidates(records_result=records_result)

    assert result["valid_for_testnet_dry_run"] is False


def test_safety_flags(tmp_path):
    result = validate_real_ohlcv_gap_candidates()
    assert result["allowed_mode"] == "SHADOW_ONLY"
    assert result["collection_mode"] == "SHADOW_COLLECTION"
    assert result["submit_permission"] == "NO_SUBMIT"
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False
    assert result["submit_attempted"] is False
    assert result["cancel_attempted"] is False
    assert result["flatten_attempted"] is False


def test_json_flag_works(tmp_path):
    project_root = str(Path(__file__).parent.parent.parent)
    proc = subprocess.Popen(
        [sys.executable, str(Path(project_root) / "scripts" / "validate_real_ohlcv_gap_candidates.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root,
        env={**os.environ, "QQ_RUNTIME_MODE": "dry-run", "PYTHONPATH": project_root}
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T416"
