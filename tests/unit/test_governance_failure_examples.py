"""Tests for governance failure deterministic examples factory."""

from __future__ import annotations

import pytest

from core.governance_failure_examples import (
    build_blocked_example_failures,
    build_example_packet,
    build_example_report,
    build_fail_example_failures,
    build_mixed_example_failures,
    build_pass_example_failures,
    build_warn_example_failures,
)


# ── failure builder tests ────────────────────────────────────────────


class TestBuildPassExampleFailures:
    def test_returns_empty_list(self):
        assert build_pass_example_failures() == []


class TestBuildWarnExampleFailures:
    def test_returns_warning_level_failures(self):
        failures = build_warn_example_failures()
        assert len(failures) > 0
        for f in failures:
            assert f.severity.value == "warning"

    def test_all_retryable(self):
        failures = build_warn_example_failures()
        for f in failures:
            assert f.retryable is True

    def test_deterministic(self):
        a = build_warn_example_failures()
        b = build_warn_example_failures()
        assert len(a) == len(b)
        for fa, fb in zip(a, b):
            assert fa.code == fb.code
            assert fa.message == fb.message
            assert fa.severity == fb.severity


class TestBuildFailExampleFailures:
    def test_returns_error_level_failure(self):
        failures = build_fail_example_failures()
        assert len(failures) > 0
        has_error = any(f.severity.value == "error" for f in failures)
        assert has_error


class TestBuildBlockedExampleFailures:
    def test_returns_critical_non_retryable(self):
        failures = build_blocked_example_failures()
        assert len(failures) > 0
        for f in failures:
            assert f.severity.value == "critical"
            assert f.retryable is False


class TestBuildMixedExampleFailures:
    def test_returns_multiple_severities(self):
        failures = build_mixed_example_failures()
        severities = {f.severity.value for f in failures}
        assert len(severities) > 1

    def test_deterministic(self):
        a = build_mixed_example_failures()
        b = build_mixed_example_failures()
        assert len(a) == len(b)
        for fa, fb in zip(a, b):
            assert fa.code == fb.code
            assert fa.severity == fb.severity


# ── report builder tests ─────────────────────────────────────────────


class TestBuildExampleReport:
    @pytest.mark.parametrize("kind", ["pass", "warn", "fail", "blocked", "mixed"])
    def test_returns_dict(self, kind):
        report = build_example_report(kind)
        assert isinstance(report, dict)
        assert "verdict" in report
        assert "total_failures" in report

    def test_pass_verdict(self):
        report = build_example_report("pass")
        assert report["verdict"] == "PASS"
        assert report["total_failures"] == 0

    def test_warn_verdict(self):
        report = build_example_report("warn")
        assert report["verdict"] == "WARN"

    def test_fail_verdict(self):
        report = build_example_report("fail")
        assert report["verdict"] == "FAIL"

    def test_blocked_verdict(self):
        report = build_example_report("blocked")
        assert report["verdict"] == "BLOCKED"

    def test_unsupported_kind_raises(self):
        with pytest.raises(ValueError, match="Unsupported kind"):
            build_example_report("invalid")


# ── packet builder tests ─────────────────────────────────────────────


class TestBuildExamplePacket:
    @pytest.mark.parametrize("kind", ["pass", "warn", "fail", "blocked", "mixed"])
    def test_returns_dict(self, kind):
        packet = build_example_packet(kind)
        assert isinstance(packet, dict)
        assert "report" in packet
        assert "final_verdict" in packet

    def test_unsupported_kind_raises(self):
        with pytest.raises(ValueError, match="Unsupported kind"):
            build_example_packet("invalid")


# ── determinism tests ────────────────────────────────────────────────


class TestDeterminism:
    @pytest.mark.parametrize("kind", ["warn", "fail", "blocked", "mixed"])
    def test_repeated_report_calls_equivalent(self, kind):
        a = build_example_report(kind)
        b = build_example_report(kind)
        assert a == b

    @pytest.mark.parametrize("kind", ["warn", "fail", "blocked", "mixed"])
    def test_repeated_packet_calls_equivalent(self, kind):
        a = build_example_packet(kind)
        b = build_example_packet(kind)
        assert a == b
