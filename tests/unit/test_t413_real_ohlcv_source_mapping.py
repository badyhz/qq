import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.generate_real_ohlcv_source_mapping_v1 import generate_real_ohlcv_source_mapping_v1


def test_kline_cache_path_derived_symbol_timeframe(tmp_path):
    # Create a kline CSV in tmp_path
    data_dir = tmp_path / "data" / "cache" / "klines" / "BNBUSDT" / "1m"
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "2025-10-15.csv"
    csv_content = """open_time_ms,open,high,low,close,volume,close_time_ms,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore,open_time,close_time
1760579200000,580.0,590.0,570.0,585.0,10000.0,1760582799999,5850000.0,100,5000.0,2925000.0,0,1760579200,1760582799
"""
    csv_path.write_text(csv_content)

    # Create a source audit for this file
    source_audits = [
        {
            "source_id": "test-1",
            "path": str(csv_path),
            "columns": ["open_time_ms", "open", "high", "low", "close", "volume", "close_time_ms", "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore", "open_time", "close_time"],
            "has_open": True,
            "has_high": True,
            "has_low": True,
            "has_close": True,
            "has_volume": True
        }
    ]

    result = generate_real_ohlcv_source_mapping_v1(source_audits=source_audits)

    assert result["selected_source_count"] >= 1
    selected = result["selected_sources"][0]
    assert selected["mapping_ready"]
    assert selected["field_mappings"]["symbol"] == "PATH_SYMBOL"
    assert selected["field_mappings"]["timeframe"] == "PATH_TIMEFRAME"
    assert selected["path_derived_fields"]["symbol"] == "BNBUSDT"
    assert selected["path_derived_fields"]["timeframe"] == "1m"
    assert selected["field_mappings"]["timestamp"] in ["open_time_ms", "open_time", "close_time"]


def test_missing_ohlcv_fields_not_selected(tmp_path):
    # Create CSV missing volume
    data_dir = tmp_path / "data" / "cache" / "klines" / "BTCUSDT" / "1m"
    data_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "2025-10-15.csv"
    csv_path.write_text("open_time_ms,open,high,low,close\n1760579200000,60000,61000,59000,60500\n")

    source_audits = [
        {
            "source_id": "test-2",
            "path": str(csv_path),
            "columns": ["open_time_ms", "open", "high", "low", "close"],
            "has_open": True,
            "has_high": True,
            "has_low": True,
            "has_close": True,
            "has_volume": False
        }
    ]

    result = generate_real_ohlcv_source_mapping_v1(source_audits=source_audits)

    assert result["selected_source_count"] == 0


def test_price_only_source_not_selected(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    csv_path = data_dir / "price_only.csv"
    csv_path.write_text("timestamp,price\n1760579200000,60000\n")

    source_audits = [
        {
            "source_id": "test-3",
            "path": str(csv_path),
            "columns": ["timestamp", "price"],
            "has_open": False,
            "has_high": False,
            "has_low": False,
            "has_close": True,  # only price
            "has_volume": False
        }
    ]

    result = generate_real_ohlcv_source_mapping_v1(source_audits=source_audits)

    assert result["selected_source_count"] == 0


def test_fallback_values_used_false(tmp_path):
    source_audits = []
    result = generate_real_ohlcv_source_mapping_v1(source_audits=source_audits)
    assert result["fallback_values_used"] is False


def test_safety_flags(tmp_path):
    source_audits = []
    result = generate_real_ohlcv_source_mapping_v1(source_audits=source_audits)
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
        [sys.executable, str(Path(__file__).parent.parent.parent / "scripts" / "generate_real_ohlcv_source_mapping_v1.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()
    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert result_json["task_id"] == "T413"
