"""Integration test for system dry-run E2E pipeline."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.runtime_integrations.e2e.system_dry_run_e2e import run_e2e


def test_e2e_runs_with_fixture_data():
    """E2E pipeline runs and produces all expected artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        data_dir = tmp / "data"
        reports_dir = tmp / "reports"
        data_dir.mkdir()
        reports_dir.mkdir()

        # Create fixture x_exports data
        x_dir = data_dir / "x_exports"
        x_dir.mkdir(parents=True)
        fixture = '{"tickers": ["BTC", "ETH"], "timestamp": "2026-06-01", "source_file": "test.md"}\n'
        (x_dir / "test.jsonl").write_text(fixture, encoding="utf-8")

        result = run_e2e(data_dir, reports_dir)

        assert result["status"] == "SYSTEM_DRY_RUN_E2E_PASS"
        assert "research_source_loading" in result["steps_completed"]
        assert "shadow_runtime" in result["steps_completed"]
        assert "testnet_simulation" in result["steps_completed"]
        assert "alert_runtime" in result["steps_completed"]
        assert "feishu_payloads" in result["steps_completed"]
        assert "operator_state" in result["steps_completed"]
        assert "dashboard" in result["steps_completed"]
        assert "e2e_report" in result["steps_completed"]


def test_e2e_produces_shadow_signals():
    """Shadow signals are generated from research data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        data_dir = tmp / "data"
        reports_dir = tmp / "reports"
        data_dir.mkdir()
        reports_dir.mkdir()

        x_dir = data_dir / "x_exports"
        x_dir.mkdir(parents=True)
        fixture = '{"tickers": ["BTC", "ETH", "SOL"], "timestamp": "2026-06-01", "source_file": "test.md"}\n'
        (x_dir / "test.jsonl").write_text(fixture, encoding="utf-8")

        run_e2e(data_dir, reports_dir)

        signals_path = data_dir / "runtime" / "shadow" / "signals.jsonl"
        assert signals_path.exists()
        lines = [l for l in signals_path.read_text().strip().splitlines() if l.strip()]
        assert len(lines) > 0
        signal = json.loads(lines[0])
        assert "ticker" in signal
        assert signal["shadow_only"] is True
        assert signal["no_submit"] is True


def test_e2e_alerts_consume_shadow_signals():
    """Alerts are generated from shadow signal output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        data_dir = tmp / "data"
        reports_dir = tmp / "reports"
        data_dir.mkdir()
        reports_dir.mkdir()

        x_dir = data_dir / "x_exports"
        x_dir.mkdir(parents=True)
        fixture = '{"tickers": ["BTC"], "timestamp": "2026-06-01", "source_file": "test.md"}\n'
        (x_dir / "test.jsonl").write_text(fixture, encoding="utf-8")

        run_e2e(data_dir, reports_dir)

        alerts_path = data_dir / "runtime" / "alerts" / "alerts.jsonl"
        assert alerts_path.exists()
        lines = [l for l in alerts_path.read_text().strip().splitlines() if l.strip()]
        assert len(lines) > 0
        alert = json.loads(lines[0])
        assert alert["source"] in ("research", "shadow", "testnet_sim")
        assert alert["dry_run"] is True


def test_e2e_dashboard_reads_runtime_state():
    """Dashboard HTML is generated from runtime operator state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        data_dir = tmp / "data"
        reports_dir = tmp / "reports"
        data_dir.mkdir()
        reports_dir.mkdir()

        x_dir = data_dir / "x_exports"
        x_dir.mkdir(parents=True)
        fixture = '{"tickers": ["BTC"], "timestamp": "2026-06-01", "source_file": "test.md"}\n'
        (x_dir / "test.jsonl").write_text(fixture, encoding="utf-8")

        run_e2e(data_dir, reports_dir)

        # Verify state file exists
        state_path = data_dir / "runtime" / "operator" / "system_state.json"
        assert state_path.exists()
        state = json.loads(state_path.read_text())
        assert state["current_mode"] == "ACTUAL_DRY_RUN"
        assert state["submit_permission"] == "NO_SUBMIT"

        # Verify dashboard exists and contains runtime data
        dash_path = reports_dir / "operator_dashboard.html"
        assert dash_path.exists()
        html = dash_path.read_text()
        assert "ACTUAL_DRY_RUN" in html
        assert "NO_SUBMIT" in html
        assert "NOT ALLOWED" in html


def test_e2e_no_submit_evidence_written():
    """No-submit evidence is produced by testnet simulation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        data_dir = tmp / "data"
        reports_dir = tmp / "reports"
        data_dir.mkdir()
        reports_dir.mkdir()

        x_dir = data_dir / "x_exports"
        x_dir.mkdir(parents=True)
        fixture = '{"tickers": ["BTC", "ETH"], "timestamp": "2026-06-01", "source_file": "test.md"}\n'
        (x_dir / "test.jsonl").write_text(fixture, encoding="utf-8")

        run_e2e(data_dir, reports_dir)

        evidence_path = data_dir / "runtime" / "testnet_sim" / "no_submit_evidence.jsonl"
        assert evidence_path.exists()
        data = json.loads(evidence_path.read_text())
        assert len(data) > 0
        assert data[0]["dry_run"] is True


def test_e2e_feishu_payloads_are_dry_run():
    """Feishu payloads are marked as dry-run and not actually sent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = pathlib.Path(tmpdir)
        data_dir = tmp / "data"
        reports_dir = tmp / "reports"
        data_dir.mkdir()
        reports_dir.mkdir()

        x_dir = data_dir / "x_exports"
        x_dir.mkdir(parents=True)
        fixture = '{"tickers": ["BTC"], "timestamp": "2026-06-01", "source_file": "test.md"}\n'
        (x_dir / "test.jsonl").write_text(fixture, encoding="utf-8")

        run_e2e(data_dir, reports_dir)

        payloads_path = data_dir / "runtime" / "alerts" / "feishu_dry_run_payloads.jsonl"
        assert payloads_path.exists()
        lines = [l for l in payloads_path.read_text().strip().splitlines() if l.strip()]
        assert len(lines) > 0
        payload = json.loads(lines[0])
        assert payload["dry_run"] is True
        assert payload["actually_sent"] is False
