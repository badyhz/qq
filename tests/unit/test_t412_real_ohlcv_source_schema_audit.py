import pytest
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.audit_real_ohlcv_source_schema import audit_real_ohlcv_source_schema, audit_single_source


def test_complete_ohlcv_csv(tmp_path):
    # Create a complete OHLCV CSV in tmp_path/data
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_path = data_dir / "test_ohlcv.csv"
    csv_content = """timestamp,symbol,timeframe,open,high,low,close,volume
1715000000,BTCUSDT,5m,60000.0,61000.0,59000.0,60500.0,100.0
1715000300,BTCUSDT,5m,60500.0,61500.0,59500.0,61000.0,150.0
"""
    csv_path.write_text(csv_content)
    
    # Mock candidate sources
    candidate_sources = [
        {
            "source_id": "test-1",
            "path": str(csv_path)
        }
    ]
    
    result = audit_real_ohlcv_source_schema(candidate_sources=candidate_sources)
    assert result["ohlcv_ready_source_count"] >= 1
    assert result["source_audits"][0]["schema_ready"] is True
    assert result["source_audits"][0]["ohlcv_complete_records"] > 0
    assert result["source_audits"][0]["timestamp_parseable_records"] > 0
    assert result["schema_audit_ready"] is True


def test_incomplete_ohlcv_csv_missing_volume(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_path = data_dir / "test_incomplete.csv"
    csv_content = """timestamp,symbol,timeframe,open,high,low,close
1715000000,BTCUSDT,5m,60000.0,61000.0,59000.0,60500.0
"""
    csv_path.write_text(csv_content)
    
    candidate_sources = [{"source_id": "test-2", "path": str(csv_path)}]
    result = audit_real_ohlcv_source_schema(candidate_sources=candidate_sources)
    assert result["source_audits"][0]["schema_ready"] is False
    assert result["ohlcv_ready_source_count"] == 0
    assert "missing" in result["source_audits"][0]["reason"].lower() or "incomplete" in result["source_audits"][0]["reason"].lower()


def test_price_only_csv(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_path = data_dir / "test_price_only.csv"
    csv_content = """timestamp,symbol,price
1715000000,BTCUSDT,60000.0
"""
    csv_path.write_text(csv_content)
    
    candidate_sources = [{"source_id": "test-3", "path": str(csv_path)}]
    result = audit_real_ohlcv_source_schema(candidate_sources=candidate_sources)
    assert result["source_audits"][0]["schema_ready"] is False
    assert result["ohlcv_ready_source_count"] == 0


def test_safety_flags(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    result = audit_real_ohlcv_source_schema(candidate_sources=[])
    
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
    
    project_root = str(Path(__file__).parent.parent.parent)
    proc = subprocess.Popen(
        [sys.executable, str(Path(project_root) / "scripts" / "audit_real_ohlcv_source_schema.py"), "--json"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root,
        env={**os.environ, "QQ_RUNTIME_MODE": "dry-run", "PYTHONPATH": project_root}
    )
    stdout, stderr = proc.communicate()
    
    assert proc.returncode == 0
    result_json = json.loads(stdout)
    assert "task_id" in result_json
    assert result_json["task_id"] == "T412"
