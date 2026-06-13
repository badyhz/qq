"""Integration tests for replay harness."""
from __future__ import annotations
import json, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.runtime_integrations.replay.replay_harness import run_replay
from src.runtime_integrations.replay.artifact_comparator import compare_artifacts, EXPECTED_ARTIFACTS


def test_replay_runs_and_passes():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        data_dir = tmp / "data"
        reports_dir = tmp / "reports"
        data_dir.mkdir(); reports_dir.mkdir()
        x_dir = data_dir / "x_exports"; x_dir.mkdir(parents=True)
        (x_dir / "test.jsonl").write_text('{"tickers": ["BTC"], "timestamp": "2026-06-01", "source_file": "t.md"}\n')
        manifest = run_replay(2, data_dir, reports_dir)
        assert manifest.all_passed
        assert manifest.total_runs == 2


def test_replay_results_consistent():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        data_dir = tmp / "data"
        reports_dir = tmp / "reports"
        data_dir.mkdir(); reports_dir.mkdir()
        x_dir = data_dir / "x_exports"; x_dir.mkdir(parents=True)
        (x_dir / "test.jsonl").write_text('{"tickers": ["BTC", "ETH"], "timestamp": "2026-06-01", "source_file": "t.md"}\n')
        manifest = run_replay(3, data_dir, reports_dir)
        statuses = [r.status for r in manifest.results]
        assert all(s == "SYSTEM_DRY_RUN_E2E_PASS" for s in statuses)


def test_expected_artifacts_list():
    assert len(EXPECTED_ARTIFACTS) == 13
