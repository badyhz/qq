"""Tests for scripts/audit_historical_ohlcv_fixture.py — 8+ tests via subprocess."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "audit_historical_ohlcv_fixture.py"
FIX = Path(__file__).resolve().parent.parent / "fixtures" / "historical_backtest_lab"


def _run(*args, **kwargs) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT)] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


class TestAuditCli:
    def test_clean_csv_exit_0(self):
        r = _run("--input-csv", str(FIX / "btc_5m_clean.csv"),
                 "--symbol", "BTC", "--timeframe", "5m")
        assert r.returncode == 0
        assert "Clean: YES" in r.stdout

    def test_dirty_csv_exit_0(self):
        r = _run("--input-csv", str(FIX / "btc_5m_with_gaps.csv"),
                 "--symbol", "BTC", "--timeframe", "5m")
        assert r.returncode == 0
        assert "Clean: NO" in r.stdout

    def test_missing_file_exit_1(self):
        r = _run("--input-csv", "/nonexistent.csv")
        assert r.returncode == 1
        assert "ERROR" in r.stderr

    def test_json_output(self, tmp_path):
        out = tmp_path / "report.json"
        r = _run("--input-csv", str(FIX / "btc_5m_clean.csv"),
                 "--symbol", "BTC", "--timeframe", "5m",
                 "--output-json", str(out))
        assert r.returncode == 0
        data = json.loads(out.read_text())
        assert data["symbol"] == "BTC"
        assert data["is_clean"] is True
        assert data["total_rows"] == 50

    def test_md_output(self, tmp_path):
        out = tmp_path / "report.md"
        r = _run("--input-csv", str(FIX / "btc_5m_clean.csv"),
                 "--symbol", "BTC", "--timeframe", "5m",
                 "--output-md", str(out))
        assert r.returncode == 0
        md = out.read_text()
        assert "# OHLCV Quality Report" in md
        assert "BTC" in md

    def test_gaps_in_json(self, tmp_path):
        out = tmp_path / "report.json"
        r = _run("--input-csv", str(FIX / "btc_5m_with_gaps.csv"),
                 "--symbol", "BTC", "--timeframe", "5m",
                 "--output-json", str(out))
        assert r.returncode == 0
        data = json.loads(out.read_text())
        assert data["gap_count"] == 3
        assert data["is_clean"] is False

    def test_duplicates_in_json(self, tmp_path):
        out = tmp_path / "report.json"
        r = _run("--input-csv", str(FIX / "btc_5m_with_duplicates.csv"),
                 "--symbol", "BTC", "--timeframe", "5m",
                 "--output-json", str(out))
        assert r.returncode == 0
        data = json.loads(out.read_text())
        assert data["duplicate_count"] == 5
        assert data["is_clean"] is False

    def test_chunk_size_flag(self):
        r = _run("--input-csv", str(FIX / "btc_5m_clean.csv"),
                 "--symbol", "BTC", "--timeframe", "5m",
                 "--chunk-size", "10")
        assert r.returncode == 0
        assert "Clean: YES" in r.stdout

    def test_stdout_summary_format(self):
        r = _run("--input-csv", str(FIX / "btc_5m_clean.csv"),
                 "--symbol", "BTC", "--timeframe", "5m")
        assert r.returncode == 0
        assert "Rows: 50" in r.stdout
        assert "Valid: 50" in r.stdout
        assert "Dup: 0" in r.stdout

    def test_invalid_ohlcv_detected(self, tmp_path):
        out = tmp_path / "report.json"
        r = _run("--input-csv", str(FIX / "btc_5m_invalid_ohlcv.csv"),
                 "--symbol", "BTC", "--timeframe", "5m",
                 "--output-json", str(out))
        assert r.returncode == 0
        data = json.loads(out.read_text())
        assert data["is_clean"] is False
