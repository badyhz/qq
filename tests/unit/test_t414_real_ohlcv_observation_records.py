import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.build_real_ohlcv_observation_records import build_real_ohlcv_observation_records


def test_complete_kline_csv_builds_records(tmp_path):
    data_dir = tmp_path / "data" / "cache" / "klines" / "BNBUSDT" / "1m"
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "2025-10-15.csv"
    csv_content = """open_time_ms,open,high,low,close,volume,close_time_ms,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore,open_time,close_time
1760579200000,580.0,590.0,570.0,585.0,10000.0,1760582799999,5850000.0,100,5000.0,2925000.0,0,1760579200,1760582799
1760582800000,585.0,595.0,575.0,590.0,12000.0,1760586399999,7080000.0,120,6000.0,3540000.0,0,1760582800,1760586399
"""
    csv_path.write_text(csv_content)

    selected_sources = [
        {
            "source_id": "test-1",
            "path": str(csv_path),
            "field_mappings": {
                "timestamp": "open_time_ms",
                "symbol": "PATH_SYMBOL",
                "timeframe": "PATH_TIMEFRAME",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume"
            },
            "path_derived_fields": {
                "symbol": "BNBUSDT",
                "timeframe": "1m"
            },
            "mapping_ready": True
        }
    ]

    result = build_real_ohlcv_observation_records(selected_sources=selected_sources)

    assert result["mapping_ready"]
    assert result["records_built"] >= 2
    first_rec = result["records"][0]
    assert first_rec["symbol"] == "BNBUSDT"
    assert first_rec["timeframe"] == "1m"
    assert first_rec["observation_only"] is True
    assert first_rec["synthetic_placeholder"] is False
    assert first_rec["source_type"] == "KLINE_CACHE"


def test_missing_ohlcv_row_skipped(tmp_path):
    data_dir = tmp_path / "data" / "cache" / "klines" / "BTCUSDT" / "1m"
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "2025-10-15.csv"
    csv_content = """open_time_ms,open,high,low,close,volume
1760579200000,60000,,59000,60500,10000
"""
    csv_path.write_text(csv_content)

    selected_sources = [
        {
            "source_id": "test-2",
            "path": str(csv_path),
            "field_mappings": {"timestamp": "open_time_ms", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
            "path_derived_fields": {"symbol": "BTCUSDT", "timeframe": "1m"},
            "mapping_ready": True
        }
    ]

    result = build_real_ohlcv_observation_records(selected_sources=selected_sources)

    assert result["records_skipped_missing_ohlcv"] >= 1


def test_invalid_timestamp_skipped(tmp_path):
    data_dir = tmp_path / "data" / "cache" / "klines" / "BTCUSDT" / "1m"
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "2025-10-15.csv"
    csv_content = """open_time_ms,open,high,low,close,volume
invalid_ts,60000,61000,59000,60500,10000
"""
    csv_path.write_text(csv_content)

    selected_sources = [
        {
            "source_id": "test-3",
            "path": str(csv_path),
            "field_mappings": {"timestamp": "open_time_ms", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"},
            "path_derived_fields": {"symbol": "BTCUSDT", "timeframe": "1m"},
            "mapping_ready": True
        }
    ]

    result = build_real_ohlcv_observation_records(selected_sources=selected_sources)

    assert result["records_skipped_invalid_timestamp"] >= 1


def test_fallback_values_used_false(tmp_path):
    result = build_real_ohlcv_observation_records(selected_sources=[])
    assert result["fallback_values_used"] is False


def test_safety_flags(tmp_path):
    result = build_real_ohlcv_observation_records(selected_sources=[])
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
        [sys.executable, str(Path(__file__).parent.parent.parent / "scripts" / "build_real_ohlcv_observation_records.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()
    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T414"
