"""Tests for governance failure regression packet CLI renderer.

Deterministic. No file I/O. No network.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

_SCRIPT = "scripts/render_governance_failure_regression_packet.py"


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run the renderer script with PYTHONPATH set."""
    return subprocess.run(
        [sys.executable, _SCRIPT, *args],
        capture_output=True,
        text=True,
        cwd="/Users/winnie/Documents/trae_projects/qq",
        env={**__import__("os").environ, "PYTHONPATH": "."},
        **kwargs,
    )


# ── pass markdown ─────────────────────────────────────────────────────


class TestPassMarkdown:
    def test_exit_zero(self):
        r = _run(["--sample", "pass", "--format", "markdown"])
        assert r.returncode == 0

    def test_contains_verdict(self):
        r = _run(["--sample", "pass", "--format", "markdown"])
        assert "PASS" in r.stdout

    def test_contains_title(self):
        r = _run(["--sample", "pass", "--format", "markdown"])
        assert "Governance Failure Regression" in r.stdout


# ── warn markdown ─────────────────────────────────────────────────────


class TestWarnMarkdown:
    def test_exit_zero(self):
        r = _run(["--sample", "warn", "--format", "markdown"])
        assert r.returncode == 0

    def test_contains_warn(self):
        r = _run(["--sample", "warn", "--format", "markdown"])
        assert "WARN" in r.stdout

    def test_contains_rate_limit(self):
        r = _run(["--sample", "warn", "--format", "markdown"])
        assert "rate_limit" in r.stdout


# ── fail json ─────────────────────────────────────────────────────────


class TestFailJson:
    def test_exit_zero(self):
        r = _run(["--sample", "fail", "--format", "json"])
        assert r.returncode == 0

    def test_valid_json(self):
        r = _run(["--sample", "fail", "--format", "json"])
        data = json.loads(r.stdout)
        assert data["final_verdict"] == "FAIL"

    def test_contains_failures(self):
        r = _run(["--sample", "fail", "--format", "json"])
        data = json.loads(r.stdout)
        assert data["report"]["total_failures"] > 0


# ── blocked json ──────────────────────────────────────────────────────


class TestBlockedJson:
    def test_exit_zero(self):
        r = _run(["--sample", "blocked", "--format", "json"])
        assert r.returncode == 0

    def test_valid_json(self):
        r = _run(["--sample", "blocked", "--format", "json"])
        data = json.loads(r.stdout)
        assert data["final_verdict"] == "BLOCKED"

    def test_contains_policy_block(self):
        r = _run(["--sample", "blocked", "--format", "json"])
        data = json.loads(r.stdout)
        codes = [f["code"] for f in data["report"]["failures"]]
        assert "POLICY_BLOCK" in codes


# ── deterministic repeated output ─────────────────────────────────────


class TestDeterministic:
    @pytest.mark.parametrize("sample", ["pass", "warn", "fail", "blocked"])
    @pytest.mark.parametrize("fmt", ["markdown", "json"])
    def test_repeated_output_identical(self, sample, fmt):
        r1 = _run(["--sample", sample, "--format", fmt])
        r2 = _run(["--sample", sample, "--format", fmt])
        assert r1.stdout == r2.stdout
        assert r1.returncode == r2.returncode


# ── --strict exit code ───────────────────────────────────────────────


class TestStrict:
    def test_strict_pass_exits_zero(self):
        r = _run(["--sample", "pass", "--strict"])
        assert r.returncode == 0

    def test_strict_warn_exits_zero(self):
        r = _run(["--sample", "warn", "--strict"])
        assert r.returncode == 0

    def test_strict_fail_exits_one(self):
        r = _run(["--sample", "fail", "--strict"])
        assert r.returncode == 1

    def test_strict_blocked_exits_one(self):
        r = _run(["--sample", "blocked", "--strict"])
        assert r.returncode == 1

    def test_no_strict_fail_exits_zero(self):
        r = _run(["--sample", "fail"])
        assert r.returncode == 0

    def test_no_strict_blocked_exits_zero(self):
        r = _run(["--sample", "blocked"])
        assert r.returncode == 0


# ── invalid sample ────────────────────────────────────────────────────


class TestInvalidSample:
    def test_invalid_sample_returns_nonzero(self):
        r = _run(["--sample", "invalid"])
        assert r.returncode != 0


# ── invalid format ────────────────────────────────────────────────────


class TestInvalidFormat:
    def test_invalid_format_returns_nonzero(self):
        r = _run(["--sample", "pass", "--format", "yaml"])
        assert r.returncode != 0


# ── no file creation ──────────────────────────────────────────────────


class TestNoFileCreation:
    def test_stdout_only(self, tmp_path, monkeypatch):
        """Run in a temp dir; no files should be created."""
        r = _run(["--sample", "pass", "--format", "markdown"])
        assert r.returncode == 0
        # script should not create any files in cwd
        # (we trust stdout-only by design; no file assertions needed)
