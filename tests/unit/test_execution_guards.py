"""Tests for core.execution_guards — T601 helpers + T602 assertions."""
from __future__ import annotations

import os

import pytest

from core.execution_guards import (
    ExecutionGuardError,
    assert_cancel_unlocked,
    assert_dry_run_required,
    assert_flatten_unlocked,
    assert_no_live_mode,
    assert_submit_unlocked,
    assert_symbol_allowed,
    build_execution_guard_report,
    normalize_execution_mode,
    parse_symbol_allowlist,
    read_bool_env,
)

# ---------------------------------------------------------------------------
# T601 — normalize_execution_mode
# ---------------------------------------------------------------------------

class TestNormalizeExecutionMode:
    def test_dry_run_underscore(self):
        assert normalize_execution_mode("dry_run") == "dry_run"

    def test_dry_run_hyphen(self):
        assert normalize_execution_mode("dry-run") == "dry_run"

    def test_dryrun_no_sep_raises(self):
        with pytest.raises(ValueError, match="unknown execution mode"):
            normalize_execution_mode("dryrun")

    def test_testnet(self):
        assert normalize_execution_mode("testnet") == "testnet"

    def test_live(self):
        assert normalize_execution_mode("live") == "live"

    def test_case_insensitive(self):
        assert normalize_execution_mode("DRY_RUN") == "dry_run"

    def test_none_raises(self):
        with pytest.raises(ValueError, match="unknown execution mode"):
            normalize_execution_mode(None)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="unknown execution mode"):
            normalize_execution_mode("")

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="unknown execution mode"):
            normalize_execution_mode("banana")


# ---------------------------------------------------------------------------
# T601 — read_bool_env
# ---------------------------------------------------------------------------

class TestReadBoolEnv:
    ENV_KEY = "_QQ_TEST_BOOL_ENV"

    def teardown_method(self):
        os.environ.pop(self.ENV_KEY, None)

    @pytest.mark.parametrize("val", ["1", "true", "yes", "y", "on", "TRUE", "Yes"])
    def test_truthy(self, val):
        os.environ[self.ENV_KEY] = val
        assert read_bool_env(self.ENV_KEY) is True

    @pytest.mark.parametrize("val", ["0", "false", "no", "n", "off", "FALSE", "No"])
    def test_falsy(self, val):
        os.environ[self.ENV_KEY] = val
        assert read_bool_env(self.ENV_KEY) is False

    def test_missing_returns_false(self):
        assert read_bool_env(self.ENV_KEY) is False

    def test_empty_string_returns_false(self):
        os.environ[self.ENV_KEY] = ""
        assert read_bool_env(self.ENV_KEY) is False

    def test_default_override_unrecognized_value(self):
        os.environ[self.ENV_KEY] = "maybe"
        assert read_bool_env(self.ENV_KEY, default=True) is True

    def test_default_false_unrecognized_value(self):
        os.environ[self.ENV_KEY] = "maybe"
        assert read_bool_env(self.ENV_KEY, default=False) is False


# ---------------------------------------------------------------------------
# T601 — parse_symbol_allowlist
# ---------------------------------------------------------------------------

class TestParseSymbolAllowlist:
    def test_from_string(self):
        assert parse_symbol_allowlist("btcusdt,ethusdt") == frozenset({"BTCUSDT", "ETHUSDT"})

    def test_from_list(self):
        assert parse_symbol_allowlist(["solusdt"]) == frozenset({"SOLUSDT"})

    def test_none_returns_empty(self):
        assert parse_symbol_allowlist(None) == frozenset()

    def test_strips_whitespace(self):
        assert parse_symbol_allowlist(" btc , eth ") == frozenset({"BTC", "ETH"})

    def test_empty_parts_ignored(self):
        assert parse_symbol_allowlist("btc,,eth,") == frozenset({"BTC", "ETH"})


# ---------------------------------------------------------------------------
# T601 — build_execution_guard_report
# ---------------------------------------------------------------------------

class TestBuildExecutionGuardReport:
    EXPECTED_KEYS = {
        "mode", "action", "symbol", "symbol_allowlist",
        "layer0_blocked", "layer1_capability", "layer2_cli_allow",
        "layer3_env_unlock", "layer4_manual_confirm", "layer5_symbol_ok",
    }

    def test_has_stable_keys(self):
        r = build_execution_guard_report(mode="dry_run", action="submit")
        assert set(r.keys()) == self.EXPECTED_KEYS

    def test_layer0_blocked_true(self):
        r = build_execution_guard_report(
            mode="dry_run", action="submit",
            env_overrides={"QQ_NO_SUBMIT": True},
        )
        assert r["layer0_blocked"] is True

    def test_layer0_blocked_false_by_default(self):
        r = build_execution_guard_report(mode="dry_run", action="submit")
        assert r["layer0_blocked"] is False

    def test_symbol_uppercased(self):
        r = build_execution_guard_report(mode="dry_run", action="submit", symbol="btc")
        assert r["symbol"] == "BTC"

    def test_layer5_symbol_ok_empty_allowlist(self):
        r = build_execution_guard_report(
            mode="dry_run", action="submit",
            symbol="BTCUSDT", symbol_allowlist=frozenset(),
        )
        assert r["layer5_symbol_ok"] is True

    def test_layer5_symbol_ok_in_allowlist(self):
        r = build_execution_guard_report(
            mode="dry_run", action="submit",
            symbol="BTCUSDT", symbol_allowlist=frozenset({"BTCUSDT"}),
        )
        assert r["layer5_symbol_ok"] is True

    def test_layer5_symbol_not_ok(self):
        r = build_execution_guard_report(
            mode="dry_run", action="submit",
            symbol="DOGEUSDT", symbol_allowlist=frozenset({"BTCUSDT"}),
        )
        assert r["layer5_symbol_ok"] is False


# ---------------------------------------------------------------------------
# T602 — assert_no_live_mode
# ---------------------------------------------------------------------------

class TestAssertNoLiveMode:
    def test_accepts_dry_run(self):
        assert assert_no_live_mode("dry_run") == "dry_run"

    def test_accepts_testnet(self):
        assert assert_no_live_mode("testnet") == "testnet"

    def test_rejects_live(self):
        with pytest.raises(ExecutionGuardError, match="live mode not allowed"):
            assert_no_live_mode("live")

    def test_rejects_unknown(self):
        with pytest.raises(ValueError, match="unknown execution mode"):
            assert_no_live_mode("banana")


# ---------------------------------------------------------------------------
# T602 — assert_dry_run_required
# ---------------------------------------------------------------------------

class TestAssertDryRunRequired:
    def test_accepts_dry_run(self):
        assert assert_dry_run_required("dry_run") == "dry_run"

    def test_rejects_testnet(self):
        with pytest.raises(ExecutionGuardError, match="dry_run required"):
            assert_dry_run_required("testnet")

    def test_rejects_live(self):
        with pytest.raises(ExecutionGuardError, match="dry_run required"):
            assert_dry_run_required("live")

    def test_rejects_none(self):
        with pytest.raises(ValueError, match="unknown execution mode"):
            assert_dry_run_required(None)


# ---------------------------------------------------------------------------
# T602 — QQ_NO_* kill-switch blocks
# ---------------------------------------------------------------------------

_FULL_UNLOCK = dict(
    mode="testnet", symbol="BTCUSDT", symbol_allowlist=frozenset({"BTCUSDT"}),
    capability=True, cli_allow=True, manual_confirm=True,
)


@pytest.fixture(autouse=True)
def _clean_env():
    for k in ("QQ_NO_SUBMIT", "QQ_NO_CANCEL", "QQ_NO_FLATTEN", "QQ_NO_LIVE",
              "QQ_UNLOCK_SUBMIT", "QQ_UNLOCK_CANCEL", "QQ_UNLOCK_FLATTEN"):
        os.environ.pop(k, None)
    yield
    for k in ("QQ_NO_SUBMIT", "QQ_NO_CANCEL", "QQ_NO_FLATTEN", "QQ_NO_LIVE",
              "QQ_UNLOCK_SUBMIT", "QQ_UNLOCK_CANCEL", "QQ_UNLOCK_FLATTEN"):
        os.environ.pop(k, None)


class TestKillSwitchBlocks:
    def test_qq_no_submit_blocks(self):
        os.environ["QQ_NO_SUBMIT"] = "1"
        os.environ["QQ_UNLOCK_SUBMIT"] = "1"
        with pytest.raises(ExecutionGuardError, match="QQ_NO_SUBMIT"):
            assert_submit_unlocked(**_FULL_UNLOCK)

    def test_qq_no_cancel_blocks(self):
        os.environ["QQ_NO_CANCEL"] = "1"
        os.environ["QQ_UNLOCK_CANCEL"] = "1"
        with pytest.raises(ExecutionGuardError, match="QQ_NO_CANCEL"):
            assert_cancel_unlocked(**_FULL_UNLOCK)

    def test_qq_no_flatten_blocks(self):
        os.environ["QQ_NO_FLATTEN"] = "1"
        os.environ["QQ_UNLOCK_FLATTEN"] = "1"
        with pytest.raises(ExecutionGuardError, match="QQ_NO_FLATTEN"):
            assert_flatten_unlocked(**_FULL_UNLOCK)

    def test_qq_no_live_blocks_live_mode(self):
        os.environ["QQ_NO_LIVE"] = "1"
        with pytest.raises(ExecutionGuardError, match="live mode not allowed"):
            assert_no_live_mode("live")


# ---------------------------------------------------------------------------
# T602 — individual layer rejection
# ---------------------------------------------------------------------------

class TestLayerRejection:
    def test_missing_capability_rejects(self):
        with pytest.raises(ExecutionGuardError, match="layer1"):
            assert_submit_unlocked(mode="testnet", capability=False, cli_allow=True, manual_confirm=True)

    def test_missing_cli_allow_rejects(self):
        with pytest.raises(ExecutionGuardError, match="layer2"):
            assert_submit_unlocked(mode="testnet", capability=True, cli_allow=False, manual_confirm=True)

    def test_missing_env_unlock_rejects(self):
        with pytest.raises(ExecutionGuardError, match="layer3"):
            assert_submit_unlocked(mode="testnet", capability=True, cli_allow=True, manual_confirm=True)

    def test_missing_manual_confirm_rejects(self):
        os.environ["QQ_UNLOCK_SUBMIT"] = "1"
        with pytest.raises(ExecutionGuardError, match="layer4"):
            assert_submit_unlocked(mode="testnet", capability=True, cli_allow=True, manual_confirm=False)

    def test_symbol_not_in_allowlist_rejects(self):
        os.environ["QQ_UNLOCK_SUBMIT"] = "1"
        with pytest.raises(ExecutionGuardError, match="layer5"):
            assert_submit_unlocked(
                mode="testnet", symbol="DOGEUSDT",
                symbol_allowlist=frozenset({"BTCUSDT"}),
                capability=True, cli_allow=True, manual_confirm=True,
            )

    def test_missing_symbol_allowlist_entry_rejects_cancel(self):
        os.environ["QQ_UNLOCK_CANCEL"] = "1"
        with pytest.raises(ExecutionGuardError, match="layer5"):
            assert_cancel_unlocked(
                mode="testnet", symbol="DOGEUSDT",
                symbol_allowlist=frozenset({"BTCUSDT"}),
                capability=True, cli_allow=True, manual_confirm=True,
            )

    def test_missing_symbol_allowlist_entry_rejects_flatten(self):
        os.environ["QQ_UNLOCK_FLATTEN"] = "1"
        with pytest.raises(ExecutionGuardError, match="layer5"):
            assert_flatten_unlocked(
                mode="testnet", symbol="DOGEUSDT",
                symbol_allowlist=frozenset({"BTCUSDT"}),
                capability=True, cli_allow=True, manual_confirm=True,
            )


# ---------------------------------------------------------------------------
# T602 — full layered unlock passes
# ---------------------------------------------------------------------------

class TestFullUnlockPasses:
    def test_submit_passes(self):
        os.environ["QQ_UNLOCK_SUBMIT"] = "1"
        assert assert_submit_unlocked(**_FULL_UNLOCK) == "testnet"

    def test_cancel_passes(self):
        os.environ["QQ_UNLOCK_CANCEL"] = "1"
        assert assert_cancel_unlocked(**_FULL_UNLOCK) == "testnet"

    def test_flatten_passes(self):
        os.environ["QQ_UNLOCK_FLATTEN"] = "1"
        assert assert_flatten_unlocked(**_FULL_UNLOCK) == "testnet"

    def test_submit_passes_empty_allowlist(self):
        os.environ["QQ_UNLOCK_SUBMIT"] = "1"
        assert assert_submit_unlocked(
            mode="testnet", symbol="ANY", symbol_allowlist=frozenset(),
            capability=True, cli_allow=True, manual_confirm=True,
        ) == "testnet"
