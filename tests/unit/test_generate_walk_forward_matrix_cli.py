"""Tests for walk-forward matrix CLI. 8+ tests."""

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = REPO_ROOT / "scripts" / "generate_walk_forward_experiment_matrix.py"


@pytest.fixture
def fixture_dir(tmp_path):
    """Create a temporary fixture directory with sample CSVs."""
    d = tmp_path / "fixtures"
    d.mkdir()

    for symbol in ["BTCUSDT", "ETHUSDT"]:
        for tf in ["5m", "15m"]:
            csv_path = d / f"{symbol}_{tf}.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
                writer.writeheader()
                for i in range(50):
                    writer.writerow({
                        "timestamp": str(i),
                        "open": "100.0",
                        "high": "101.0",
                        "low": "99.0",
                        "close": "100.0",
                        "volume": "1.0",
                    })
    return d


class TestGenerateWalkForwardMatrixCLI:
    def test_exit_zero_on_success(self, fixture_dir, tmp_path):
        out = tmp_path / "matrix.json"
        result = subprocess.run(
            [
                sys.executable, str(CLI_PATH),
                "--fixture-dir", str(fixture_dir),
                "--symbols", "BTCUSDT,ETHUSDT",
                "--timeframes", "5m,15m",
                "--split-mode", "rolling",
                "--output-json", str(out),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    def test_output_json_exists(self, fixture_dir, tmp_path):
        out = tmp_path / "matrix.json"
        subprocess.run(
            [
                sys.executable, str(CLI_PATH),
                "--fixture-dir", str(fixture_dir),
                "--symbols", "BTCUSDT",
                "--timeframes", "5m",
                "--split-mode", "rolling",
                "--output-json", str(out),
            ],
            capture_output=True, text=True,
        )
        assert out.exists()

    def test_output_contains_expected_keys(self, fixture_dir, tmp_path):
        out = tmp_path / "matrix.json"
        subprocess.run(
            [
                sys.executable, str(CLI_PATH),
                "--fixture-dir", str(fixture_dir),
                "--symbols", "BTCUSDT",
                "--timeframes", "5m",
                "--split-mode", "rolling",
                "--output-json", str(out),
            ],
            capture_output=True, text=True,
        )
        data = json.loads(out.read_text())
        assert "symbols" in data
        assert "timeframes" in data
        assert "split_mode" in data
        assert "entries" in data

    def test_deterministic_output(self, fixture_dir, tmp_path):
        out1 = tmp_path / "m1.json"
        out2 = tmp_path / "m2.json"
        for out in [out1, out2]:
            subprocess.run(
                [
                    sys.executable, str(CLI_PATH),
                    "--fixture-dir", str(fixture_dir),
                    "--symbols", "BTCUSDT,ETHUSDT",
                    "--timeframes", "5m,15m",
                    "--split-mode", "rolling",
                    "--output-json", str(out),
                ],
                capture_output=True, text=True,
            )
        assert out1.read_text() == out2.read_text()

    def test_expanding_mode(self, fixture_dir, tmp_path):
        out = tmp_path / "matrix.json"
        result = subprocess.run(
            [
                sys.executable, str(CLI_PATH),
                "--fixture-dir", str(fixture_dir),
                "--symbols", "BTCUSDT",
                "--timeframes", "5m",
                "--split-mode", "expanding",
                "--output-json", str(out),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        data = json.loads(out.read_text())
        assert data["split_mode"] == "expanding"

    def test_missing_fixture_dir_fails(self, tmp_path):
        out = tmp_path / "matrix.json"
        result = subprocess.run(
            [
                sys.executable, str(CLI_PATH),
                "--fixture-dir", str(tmp_path / "nonexistent"),
                "--symbols", "BTCUSDT",
                "--timeframes", "5m",
                "--split-mode", "rolling",
                "--output-json", str(out),
            ],
            capture_output=True, text=True,
        )
        assert result.returncode != 0

    def test_entries_count_matches_combinations(self, fixture_dir, tmp_path):
        out = tmp_path / "matrix.json"
        subprocess.run(
            [
                sys.executable, str(CLI_PATH),
                "--fixture-dir", str(fixture_dir),
                "--symbols", "BTCUSDT,ETHUSDT",
                "--timeframes", "5m,15m",
                "--split-mode", "rolling",
                "--output-json", str(out),
            ],
            capture_output=True, text=True,
        )
        data = json.loads(out.read_text())
        assert len(data["entries"]) == 4  # 2 symbols * 2 timeframes

    def test_each_entry_has_splits(self, fixture_dir, tmp_path):
        out = tmp_path / "matrix.json"
        subprocess.run(
            [
                sys.executable, str(CLI_PATH),
                "--fixture-dir", str(fixture_dir),
                "--symbols", "BTCUSDT",
                "--timeframes", "5m",
                "--split-mode", "rolling",
                "--n-splits", "3",
                "--output-json", str(out),
            ],
            capture_output=True, text=True,
        )
        data = json.loads(out.read_text())
        for entry in data["entries"]:
            assert "splits" in entry
            assert len(entry["splits"]) > 0
