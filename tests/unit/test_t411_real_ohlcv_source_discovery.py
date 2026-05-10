import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.discover_real_ohlcv_sources import run_discovery


def test_full_ohlcv_csv(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    test_csv = data_dir / "test_ohlcv.csv"
    test_csv.write_text("timestamp,symbol,open,high,low,close,volume\n1620000000,BTCUSDT,100,110,90,105,1000\n")
    
    result = run_discovery([str(data_dir)])
    assert result["candidate_source_count"] >= 1
    assert any(cs["has_ohlcv_columns"] for cs in result["candidate_sources"])
    assert result["discovery_ready"] is True


def test_price_only_csv(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    test_csv = data_dir / "test_price.csv"
    test_csv.write_text("timestamp,symbol,price\n1620000000,BTCUSDT,100\n")
    
    result = run_discovery([str(data_dir)])
    assert all(cs["has_ohlcv_columns"] is False for cs in result["candidate_sources"])
    assert len(result["excluded_sources"]) >= 1
    assert any("missing_ohlcv" in ex["reason"].lower() for ex in result["excluded_sources"])


def test_safety_flags(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    result = run_discovery([str(data_dir)])
    assert result["allowed_mode"] == "SHADOW_ONLY"
    assert result["collection_mode"] == "SHADOW_COLLECTION"
    assert result["submit_permission"] == "NO_SUBMIT"
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False
    assert result["submit_attempted"] is False
    assert result["cancel_attempted"] is False
    assert result["flatten_attempted"] is False


def test_json_flag_works(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent.parent.parent / "scripts" / "discover_real_ohlcv_sources.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = proc.communicate()
    
    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert "task_id" in result_json
    assert result_json["task_id"] == "T411"
