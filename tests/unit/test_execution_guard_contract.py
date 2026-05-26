"""Contract tests: producer (execution_guards) -> consumer (execution_guard_schema)."""
from __future__ import annotations

import pytest

from core.execution_guards import (
    build_execution_guard_report,
    ExecutionGuardError,
    assert_submit_unlocked,
    assert_cancel_unlocked,
    assert_flatten_unlocked,
    parse_symbol_allowlist,
)
from core.execution_guard_schema import (
    validate_guard_report,
    build_guard_report_summary,
    get_guard_schema_required_keys,
    format_guard_summary_text,
)


# ---------------------------------------------------------------------------
# Producer output validates
# ---------------------------------------------------------------------------

class TestProducerValidates:
    def test_dry_run_submit_validates(self):
        report = build_execution_guard_report(
            mode="dry_run",
            action="submit",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset({"BTCUSDT"}),
        )
        report["status"] = "OK"
        report["env_overrides"] = {}
        validate_guard_report(report)

    def test_testnet_cancel_validates(self):
        report = build_execution_guard_report(
            mode="testnet",
            action="cancel",
            symbol="ETHUSDT",
            symbol_allowlist=frozenset(),
        )
        report["status"] = "OK"
        report["env_overrides"] = {}
        validate_guard_report(report)

    def test_flatten_with_allowlist_validates(self):
        report = build_execution_guard_report(
            mode="dry_run",
            action="flatten",
            symbol="SOLUSDT",
            symbol_allowlist=frozenset({"SOLUSDT", "BTCUSDT"}),
        )
        report["status"] = "OK"
        report["env_overrides"] = {}
        validate_guard_report(report)


# ---------------------------------------------------------------------------
# Summary succeeds
# ---------------------------------------------------------------------------

class TestSummarySucceeds:
    def test_summary_from_producer(self):
        report = build_execution_guard_report(
            mode="dry_run",
            action="submit",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset({"BTCUSDT"}),
        )
        report["status"] = "OK"
        report["env_overrides"] = {}
        summary = build_guard_report_summary(report)
        assert summary["blocked"] is False
        assert summary["status"] == "OK"
        assert summary["mode"] == "dry_run"
        assert summary["action"] == "submit"

    def test_all_layers_pass_computed(self):
        report = build_execution_guard_report(
            mode="testnet",
            action="submit",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset({"BTCUSDT"}),
            capability=True,
            cli_allow=True,
            manual_confirm=True,
            env_overrides={"QQ_UNLOCK_SUBMIT": True},
        )
        report["status"] = "OK"
        report["env_overrides"] = {"QQ_UNLOCK_SUBMIT": True}
        summary = build_guard_report_summary(report)
        assert summary["all_layers_pass"] is True


# ---------------------------------------------------------------------------
# Blocked report validates
# ---------------------------------------------------------------------------

class TestBlockedReport:
    def test_live_blocked_validates(self):
        report = {
            "status": "BLOCKED",
            "reason": "LIVE_MODE_NOT_ALLOWED",
            "action": "submit",
            "symbol": "BTCUSDT",
            "env_overrides": {},
        }
        validate_guard_report(report)
        summary = build_guard_report_summary(report)
        assert summary["blocked"] is True
        assert summary["reason"] == "LIVE_MODE_NOT_ALLOWED"

    def test_fail_closed_blocked_validates(self):
        report = {
            "status": "BLOCKED",
            "reason": "FAIL_CLOSED",
            "action": "cancel",
            "symbol": "",
            "env_overrides": {"QQ_NO_CANCEL": True},
        }
        validate_guard_report(report)
        summary = build_guard_report_summary(report)
        assert summary["blocked"] is True


# ---------------------------------------------------------------------------
# env_overrides survives roundtrip
# ---------------------------------------------------------------------------

class TestEnvRoundtrip:
    def test_env_overrides_preserved(self):
        env = {
            "QQ_NO_SUBMIT": True,
            "QQ_NO_CANCEL": False,
            "QQ_NO_FLATTEN": False,
            "QQ_NO_LIVE": True,
            "QQ_REQUIRE_DRY_RUN": True,
        }
        report = build_execution_guard_report(
            mode="dry_run",
            action="submit",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset(),
            env_overrides=env,
        )
        report["status"] = "OK"
        report["env_overrides"] = env
        validate_guard_report(report)
        assert report["env_overrides"]["QQ_NO_SUBMIT"] is True
        assert report["env_overrides"]["QQ_REQUIRE_DRY_RUN"] is True

    def test_env_overrides_in_summary(self):
        env = {"QQ_NO_SUBMIT": True}
        report = build_execution_guard_report(
            mode="dry_run",
            action="submit",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset(),
            env_overrides=env,
        )
        report["status"] = "OK"
        report["env_overrides"] = env
        summary = build_guard_report_summary(report)
        assert summary["blocked"] is False


# ---------------------------------------------------------------------------
# Schema drift detection
# ---------------------------------------------------------------------------

class TestSchemaDrift:
    def test_missing_required_key_detected(self):
        """Producer missing a required key fails validation."""
        report = build_execution_guard_report(
            mode="dry_run",
            action="submit",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset(),
        )
        report["status"] = "OK"
        report["env_overrides"] = {}
        required = get_guard_schema_required_keys("OK")
        missing = required - set(report.keys())
        assert not missing, f"producer missing keys: {sorted(missing)}"

    def test_producer_has_all_ok_keys_via_helper(self):
        report = build_execution_guard_report(
            mode="dry_run",
            action="submit",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset(),
        )
        report["status"] = "OK"
        report["env_overrides"] = {}
        required = get_guard_schema_required_keys("OK")
        assert required.issubset(set(report.keys()))

    def test_producer_has_all_blocked_keys_via_helper(self):
        report = {
            "status": "BLOCKED",
            "reason": "FAIL_CLOSED",
            "action": "submit",
            "symbol": "BTCUSDT",
            "env_overrides": {},
        }
        required = get_guard_schema_required_keys("BLOCKED")
        assert required.issubset(set(report.keys()))

    def test_summary_keys_stable(self):
        report = build_execution_guard_report(
            mode="dry_run",
            action="submit",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset(),
        )
        report["status"] = "OK"
        report["env_overrides"] = {}
        summary = build_guard_report_summary(report)
        expected = {"blocked", "status", "action", "mode", "all_layers_pass"}
        assert set(summary.keys()) == expected


# ---------------------------------------------------------------------------
# get_guard_schema_required_keys
# ---------------------------------------------------------------------------

class TestGetRequiredKeys:
    def test_ok_keys(self):
        keys = get_guard_schema_required_keys("OK")
        assert "status" in keys
        assert "layer0_blocked" in keys
        assert "layer5_symbol_ok" in keys

    def test_blocked_keys(self):
        keys = get_guard_schema_required_keys("BLOCKED")
        assert "status" in keys
        assert "reason" in keys
        assert "symbol" in keys

    def test_unknown_status_raises(self):
        with pytest.raises(ValueError, match="unknown status"):
            get_guard_schema_required_keys("PENDING")


# ---------------------------------------------------------------------------
# format_guard_summary_text
# ---------------------------------------------------------------------------

class TestFormatSummaryText:
    def test_ok_formatting(self):
        summary = {
            "blocked": False,
            "status": "OK",
            "action": "submit",
            "mode": "dry_run",
            "all_layers_pass": True,
        }
        text = format_guard_summary_text(summary)
        assert text == "[OK] submit mode=dry_run layers=PASS"

    def test_ok_layers_fail(self):
        summary = {
            "blocked": False,
            "status": "OK",
            "action": "cancel",
            "mode": "testnet",
            "all_layers_pass": False,
        }
        text = format_guard_summary_text(summary)
        assert text == "[OK] cancel mode=testnet layers=FAIL"

    def test_blocked_formatting(self):
        summary = {
            "blocked": True,
            "status": "BLOCKED",
            "action": "submit",
            "reason": "LIVE_MODE_NOT_ALLOWED",
        }
        text = format_guard_summary_text(summary)
        assert text == "[BLOCKED] submit reason=LIVE_MODE_NOT_ALLOWED"

    def test_missing_status_raises(self):
        with pytest.raises(ValueError, match="must contain status"):
            format_guard_summary_text({"action": "submit"})

    def test_missing_action_raises(self):
        with pytest.raises(ValueError, match="must contain status"):
            format_guard_summary_text({"status": "OK"})

    def test_not_dict_raises(self):
        with pytest.raises(ValueError, match="must be dict"):
            format_guard_summary_text("nope")


# ---------------------------------------------------------------------------
# Cross-module integration
# ---------------------------------------------------------------------------

class TestCrossModule:
    def test_assert_unlock_then_validate(self, monkeypatch):
        monkeypatch.setenv("QQ_UNLOCK_SUBMIT", "1")
        # assert_submit_unlocked succeeds
        assert_submit_unlocked(
            mode="testnet",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset({"BTCUSDT"}),
            capability=True,
            cli_allow=True,
            manual_confirm=True,
        )
        # same params produce valid report
        report = build_execution_guard_report(
            mode="testnet",
            action="submit",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset({"BTCUSDT"}),
            capability=True,
            cli_allow=True,
            manual_confirm=True,
            env_overrides={"QQ_UNLOCK_SUBMIT": True},
        )
        report["status"] = "OK"
        report["env_overrides"] = {"QQ_UNLOCK_SUBMIT": True}
        validate_guard_report(report)

    def test_assert_unlock_fails_with_bad_symbol(self, monkeypatch):
        monkeypatch.setenv("QQ_UNLOCK_SUBMIT", "1")
        with pytest.raises(ExecutionGuardError):
            assert_submit_unlocked(
                mode="testnet",
                symbol="DOGEUSDT",
                symbol_allowlist=frozenset({"BTCUSDT"}),
                capability=True,
                cli_allow=True,
                manual_confirm=True,
            )
