"""T1534 - Safety tests for frozen backlog review report CLI.

Verifies the CLI script does not use forbidden imports, network, or exchange calls.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "generate_frozen_backlog_review_report.py"


def _read_source() -> str:
    return _SCRIPT.read_text(encoding="utf-8")


class TestCLISafety:
    """Safety constraints for the CLI script."""

    def test_no_frozen_file_imports(self) -> None:
        """Must not import any of the 22 frozen untracked files."""
        source = _read_source()
        frozen_files = [
            "core/live_runner.py",
            "scripts/live_playbook.py",
            "scripts/submit_approved_candidates.py",
            "scripts/run_testnet_order_smoke.py",
            "scripts/run_signal_testnet_trial.py",
            "scripts/run_spot_testnet_acceptance.py",
            "scripts/safe_flatten_testnet_symbol.py",
            "scripts/replay_shadow_order_plans_as_testnet_dry.py",
            "scripts/submit_replayed_testnet_payload.py",
            "scripts/run_controlled_testnet_shift.py",
            "scripts/run_daily_shadow_scan_pipeline.py",
            "scripts/run_next_shadow_experiment_plan.py",
            "scripts/run_observation_shift_runtime.py",
            "scripts/run_remediation_shadow_only_loop.py",
            "scripts/run_replay_submit_batch.py",
            "scripts/run_right_breakout_param_observation.py",
            "scripts/run_right_breakout_scan_dry.py",
            "scripts/run_shadow_observation_experiments.py",
            "scripts/run_shadow_sample_collection_pipeline.py",
            "scripts/run_shadow_universe_collector.py",
            "scripts/verify_risk_release_flow.py",
            "scripts/verify_testnet_repair_scenarios.py",
        ]
        for frozen in frozen_files:
            module = frozen.replace("/", ".").replace(".py", "")
            assert module not in source, f"Script must not import frozen file: {frozen}"

    def test_no_subprocess_module_import(self) -> None:
        source = _read_source()
        assert "import subprocess" not in source
        assert "from subprocess" not in source

    def test_no_requests_or_urllib(self) -> None:
        source = _read_source()
        assert "import requests" not in source
        assert "from requests" not in source
        assert "urllib" not in source

    def test_no_network_calls(self) -> None:
        source = _read_source()
        assert "http://" not in source
        assert "https://" not in source
        assert "socket" not in source

    def test_no_exchange_or_testnet_references(self) -> None:
        source = _read_source()
        assert "binance" not in source.lower()
        assert "testnet" not in source.lower()
        assert "exchange" not in source.lower()

    def test_report_output_contains_safety_flags(self, tmp_path: "pytest.FixtureRequest") -> None:
        """Verify the generated report contains safety constraints."""
        import json
        import subprocess
        import sys

        md_path = str(tmp_path / "report.md")
        json_path = str(tmp_path / "report.json")
        result = subprocess.run(
            [sys.executable, str(_SCRIPT), "--output-md", md_path, "--output-json", json_path, "--mode", "full"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0

        # Check markdown
        md_content = Path(md_path).read_text()
        assert "**No Live:** True" in md_content
        assert "**No Submit:** True" in md_content
        assert "**No Exchange:** True" in md_content

        # Check JSON
        data = json.loads(Path(json_path).read_text())
        assert data["summary"]["no_live"] is True
        assert data["summary"]["no_submit"] is True
        assert data["summary"]["no_exchange"] is True

    def test_script_exists(self) -> None:
        assert _SCRIPT.exists(), f"CLI script not found: {_SCRIPT}"

    def test_script_is_executable_module(self) -> None:
        source = _read_source()
        assert 'if __name__ == "__main__"' in source
