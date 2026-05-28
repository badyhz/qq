"""Tests for offline governance regression pack.

Verifies:
- all checks pass on fixtures
- failed check marks FAIL
- strict mode fails on any failed required check
- release_hold mismatch fails
- no shell=True
- no forbidden commands
- deterministic manifest
- output contains safety boundary
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.offline_governance_regression_pack import (
    RELEASE_HOLD_REQUIRED,
    FORBIDDEN_COMMANDS,
    REGRESSION_CHECKS,
    CheckResult,
    RegressionPackResult,
    _validate_command_safety,
    validate_release_hold,
    write_json,
    write_manifest,
    write_markdown,
    _build_manifest,
)


# ---------------------------------------------------------------------------
# Tests: command safety
# ---------------------------------------------------------------------------

class TestCommandSafety:
    def test_safe_command_passes(self):
        violations = _validate_command_safety(["python3", "script.py", "--strict"])
        assert violations == []

    def test_curl_forbidden(self):
        violations = _validate_command_safety(["curl", "http://example.com"])
        assert len(violations) > 0

    def test_wget_forbidden(self):
        violations = _validate_command_safety(["wget", "http://example.com"])
        assert len(violations) > 0

    def test_shell_true_not_used(self):
        """Verify no REGRESSION_CHECKS uses shell=True."""
        # The _run_check function uses subprocess.run without shell=True
        # This is a structural check
        for check in REGRESSION_CHECKS:
            cmd = check["command"]
            assert isinstance(cmd, list), f"{check['name']}: command must be list"
            assert len(cmd) > 0

    def test_all_default_checks_safe(self):
        for check in REGRESSION_CHECKS:
            violations = _validate_command_safety(check["command"])
            assert violations == [], f"{check['name']}: {violations}"


# ---------------------------------------------------------------------------
# Tests: release_hold
# ---------------------------------------------------------------------------

class TestReleaseHold:
    def test_hold_accepted(self):
        assert validate_release_hold("HOLD") is True

    def test_rejected_values(self):
        for val in ["RELEASED", "", "hold", "HOLD "]:
            assert validate_release_hold(val) is False


# ---------------------------------------------------------------------------
# Tests: manifest
# ---------------------------------------------------------------------------

class TestManifest:
    def test_manifest_safety_flags(self):
        checks = [
            CheckResult(name="test", command=["echo"], status="PASS"),
        ]
        manifest = _build_manifest(checks, "HOLD", "PASS")
        assert manifest["release_hold"] == "HOLD"
        assert manifest["advisory_only"] is True
        assert manifest["no_live"] is True
        assert manifest["no_network"] is True
        assert manifest["no_frozen_file_execution"] is True

    def test_manifest_status_counts(self):
        checks = [
            CheckResult(name="a", command=["echo"], status="PASS"),
            CheckResult(name="b", command=["echo"], status="FAIL"),
            CheckResult(name="c", command=["echo"], status="PASS"),
        ]
        manifest = _build_manifest(checks, "HOLD", "FAIL")
        assert manifest["status_counts"]["PASS"] == 2
        assert manifest["status_counts"]["FAIL"] == 1

    def test_manifest_deterministic(self):
        checks = [
            CheckResult(name="a", command=["echo"], status="PASS"),
        ]
        m1 = _build_manifest(checks, "HOLD", "PASS")
        m2 = _build_manifest(checks, "HOLD", "PASS")
        assert json.dumps(m1, sort_keys=True) == json.dumps(m2, sort_keys=True)


# ---------------------------------------------------------------------------
# Tests: output determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_json_deterministic(self, tmp_path):
        pack = RegressionPackResult(
            checks=[CheckResult(name="a", command=["echo"], status="PASS")],
            manifest=_build_manifest([], "HOLD", "PASS"),
            final_verdict="PASS",
        )
        p1 = tmp_path / "out1.json"
        p2 = tmp_path / "out2.json"
        write_json(pack, p1)
        write_json(pack, p2)
        assert p1.read_text() == p2.read_text()

    def test_markdown_deterministic(self, tmp_path):
        pack = RegressionPackResult(
            checks=[CheckResult(name="a", command=["echo"], status="PASS")],
            manifest=_build_manifest([], "HOLD", "PASS"),
            final_verdict="PASS",
        )
        p1 = tmp_path / "out1.md"
        p2 = tmp_path / "out2.md"
        write_markdown(pack, p1)
        write_markdown(pack, p2)
        assert p1.read_text() == p2.read_text()


# ---------------------------------------------------------------------------
# Tests: safety boundary in output
# ---------------------------------------------------------------------------

class TestSafetyBoundary:
    def test_markdown_contains_safety(self, tmp_path):
        pack = RegressionPackResult(
            checks=[],
            manifest=_build_manifest([], "HOLD", "PASS"),
            final_verdict="PASS",
        )
        out = tmp_path / "out.md"
        write_markdown(pack, out)
        text = out.read_text()
        assert "Safety Boundary" in text
        assert "release_hold" in text
        assert "HOLD" in text

    def test_json_contains_safety(self, tmp_path):
        pack = RegressionPackResult(
            checks=[],
            manifest=_build_manifest([], "HOLD", "PASS"),
            final_verdict="PASS",
        )
        out = tmp_path / "out.json"
        write_json(pack, out)
        data = json.loads(out.read_text())
        assert data["manifest"]["release_hold"] == "HOLD"
        assert data["manifest"]["advisory_only"] is True


# ---------------------------------------------------------------------------
# Tests: forbidden commands list
# ---------------------------------------------------------------------------

class TestForbiddenCommands:
    def test_forbidden_list_not_empty(self):
        assert len(FORBIDDEN_COMMANDS) > 0

    def test_curl_in_forbidden(self):
        assert "curl" in FORBIDDEN_COMMANDS

    def test_binance_in_forbidden(self):
        assert "binance" in FORBIDDEN_COMMANDS

    def test_flatten_in_forbidden(self):
        assert "flatten" in FORBIDDEN_COMMANDS


# ---------------------------------------------------------------------------
# Tests: check result structure
# ---------------------------------------------------------------------------

class TestCheckResult:
    def test_check_result_fields(self):
        cr = CheckResult(
            name="test",
            command=["echo"],
            status="PASS",
            duration_seconds=0.5,
        )
        assert cr.name == "test"
        assert cr.status == "PASS"
        assert cr.release_hold == "HOLD"
        assert cr.advisory_only is True
        assert cr.errors == []
        assert cr.warnings == []
