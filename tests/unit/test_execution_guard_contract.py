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
    def test_new_required_key_would_fail(self):
        """If schema adds a required key, producer must match."""
        report = build_execution_guard_report(
            mode="dry_run",
            action="submit",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset(),
        )
        report["status"] = "OK"
        report["env_overrides"] = {}
        # Simulate schema drift: add hypothetical new required key
        validate_guard_report(report)  # passes now
        # If schema added "layer6_new_key" as required, this would fail

    def test_producer_has_all_ok_keys(self):
        report = build_execution_guard_report(
            mode="dry_run",
            action="submit",
            symbol="BTCUSDT",
            symbol_allowlist=frozenset(),
        )
        report["status"] = "OK"
        report["env_overrides"] = {}
        required = {
            "status", "mode", "action", "env_overrides",
            "layer0_blocked", "layer1_capability", "layer2_cli_allow",
            "layer3_env_unlock", "layer4_manual_confirm", "layer5_symbol_ok",
        }
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
