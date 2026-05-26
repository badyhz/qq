"""Tests for scripts/generate_execution_guard_status_report.py."""
from __future__ import annotations

import json
import sys
import os

import pytest

# Ensure scripts/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.generate_execution_guard_status_report import (
    generate_report,
    main,
)


class TestImportSafety:
    def test_import_script_does_not_import_high_risk(self):
        import importlib
        mod = importlib.import_module(
            "scripts.generate_execution_guard_status_report"
        )
        source = open(mod.__file__).read()
        forbidden = [
            "submit_approved_candidates",
            "submit_replayed_testnet_payload",
            "safe_flatten_testnet",
            "live_runner",
            "binance_connector",
        ]
        for name in forbidden:
            assert name not in source, f"forbidden import pattern: {name}"


class TestStdoutReport:
    def test_stdout_json(self, capsys):
        main(["--mode", "dry_run", "--action", "submit"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["status"] == "OK"
        assert report["mode"] == "dry_run"
        assert report["action"] == "submit"

    def test_stdout_json_with_symbol(self, capsys):
        main(["--mode", "testnet", "--action", "submit", "--symbol", "btcusdt"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["symbol"] == "BTCUSDT"


class TestOutputFile:
    def test_output_file_json(self, tmp_path):
        out_file = tmp_path / "report.json"
        main(["--mode", "dry_run", "--action", "cancel", "--output", str(out_file)])
        assert out_file.exists()
        report = json.loads(out_file.read_text())
        assert report["status"] == "OK"
        assert report["action"] == "cancel"


class TestMissingModeBlocked:
    def test_missing_mode_produces_blocked(self, capsys):
        main(["--action", "submit"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["status"] == "BLOCKED"
        assert report["reason"] == "FAIL_CLOSED"

    def test_unknown_mode_produces_blocked(self, capsys):
        main(["--mode", "banana", "--action", "submit"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["status"] == "BLOCKED"
        assert report["reason"] == "FAIL_CLOSED"


class TestLiveModeBlocked:
    def test_live_mode_blocked(self, capsys):
        main(["--mode", "live", "--action", "submit"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["status"] == "BLOCKED"
        assert report["reason"] == "LIVE_MODE_NOT_ALLOWED"


class TestEnvKillSwitches:
    def test_qq_no_submit_reflected(self, monkeypatch, capsys):
        monkeypatch.setenv("QQ_NO_SUBMIT", "1")
        main(["--mode", "dry_run", "--action", "submit"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["env_overrides"]["QQ_NO_SUBMIT"] is True
        assert report["layer0_blocked"] is True

    def test_qq_no_cancel_reflected(self, monkeypatch, capsys):
        monkeypatch.setenv("QQ_NO_CANCEL", "1")
        main(["--mode", "dry_run", "--action", "cancel"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["env_overrides"]["QQ_NO_CANCEL"] is True

    def test_qq_require_dry_run_reflected(self, monkeypatch, capsys):
        monkeypatch.setenv("QQ_REQUIRE_DRY_RUN", "1")
        main(["--mode", "dry_run", "--action", "submit"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["env_overrides"]["QQ_REQUIRE_DRY_RUN"] is True


class TestSymbolAllowlist:
    def test_symbol_in_allowlist_passes(self, capsys):
        main([
            "--mode", "dry_run",
            "--action", "submit",
            "--symbol", "btcusdt",
            "--symbol-allowlist", "btcusdt,ethusdt",
        ])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["layer5_symbol_ok"] is True

    def test_symbol_not_in_allowlist_rejects(self, capsys):
        main([
            "--mode", "dry_run",
            "--action", "submit",
            "--symbol", "dogeusdt",
            "--symbol-allowlist", "btcusdt,ethusdt",
        ])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["layer5_symbol_ok"] is False

    def test_empty_allowlist_allows_all(self, capsys):
        main([
            "--mode", "dry_run",
            "--action", "submit",
            "--symbol", "anyusdt",
        ])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["layer5_symbol_ok"] is True


class TestLayerFlags:
    def test_capability_flag(self, capsys):
        main(["--mode", "dry_run", "--action", "submit", "--capability"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["layer1_capability"] is True

    def test_cli_allow_flag(self, capsys):
        main(["--mode", "dry_run", "--action", "submit", "--cli-allow"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["layer2_cli_allow"] is True

    def test_manual_confirm_flag(self, capsys):
        main(["--mode", "dry_run", "--action", "submit", "--manual-confirm"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["layer4_manual_confirm"] is True


class TestGenerateReportDirect:
    def test_generate_report_blocked(self):
        report = generate_report(mode=None, action="submit")
        assert report["status"] == "BLOCKED"
        assert report["reason"] == "FAIL_CLOSED"

    def test_generate_report_ok(self):
        report = generate_report(
            mode="dry_run", action="flatten", symbol="ETHUSDT"
        )
        assert report["status"] == "OK"
        assert report["action"] == "flatten"


class TestSchemaValidationIntegration:
    def test_all_ok_reports_validate(self, capsys):
        for action in ("submit", "cancel", "flatten"):
            main(["--mode", "dry_run", "--action", action])
            captured = capsys.readouterr()
            report = json.loads(captured.out)
            assert report["status"] == "OK"

    def test_all_blocked_reports_validate(self, capsys):
        main(["--action", "submit"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["status"] == "BLOCKED"

    def test_validation_failure_produces_blocked(self, monkeypatch, capsys):
        monkeypatch.setenv("QQ_NO_SUBMIT", "1")
        main(["--mode", "dry_run", "--action", "submit"])
        captured = capsys.readouterr()
        report = json.loads(captured.out)
        assert report["status"] == "OK"
