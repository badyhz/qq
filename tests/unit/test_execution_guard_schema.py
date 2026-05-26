"""Tests for core.execution_guard_schema — pure validation only."""
from __future__ import annotations

import pytest

from core.execution_guard_schema import (
    assert_guard_report_keys,
    build_guard_report_summary,
    validate_guard_report,
)

# ---------------------------------------------------------------------------
# Fixtures — valid report shapes
# ---------------------------------------------------------------------------

def _ok_report(**overrides) -> dict:
    base = {
        "status": "OK",
        "mode": "dry_run",
        "action": "submit",
        "env_overrides": {},
        "layer0_blocked": False,
        "layer1_capability": True,
        "layer2_cli_allow": True,
        "layer3_env_unlock": False,
        "layer4_manual_confirm": False,
        "layer5_symbol_ok": True,
    }
    base.update(overrides)
    return base


def _blocked_report(**overrides) -> dict:
    base = {
        "status": "BLOCKED",
        "reason": "FAIL_CLOSED",
        "action": "submit",
        "symbol": "BTCUSDT",
        "env_overrides": {},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Valid reports pass
# ---------------------------------------------------------------------------

class TestValidReport:
    def test_ok_report_passes_keys(self):
        assert_guard_report_keys(_ok_report())

    def test_ok_report_passes_validate(self):
        validate_guard_report(_ok_report())

    def test_blocked_report_passes_keys(self):
        assert_guard_report_keys(_blocked_report())

    def test_blocked_report_passes_validate(self):
        validate_guard_report(_blocked_report())


# ---------------------------------------------------------------------------
# Missing key fails
# ---------------------------------------------------------------------------

class TestMissingKey:
    def test_ok_missing_mode(self):
        r = _ok_report()
        del r["mode"]
        with pytest.raises(ValueError, match="missing required keys"):
            assert_guard_report_keys(r)

    def test_ok_missing_layer0(self):
        r = _ok_report()
        del r["layer0_blocked"]
        with pytest.raises(ValueError, match="missing required keys"):
            assert_guard_report_keys(r)

    def test_blocked_missing_reason(self):
        r = _blocked_report()
        del r["reason"]
        with pytest.raises(ValueError, match="missing required keys"):
            assert_guard_report_keys(r)

    def test_blocked_missing_env_overrides(self):
        r = _blocked_report()
        del r["env_overrides"]
        with pytest.raises(ValueError, match="missing required keys"):
            assert_guard_report_keys(r)


# ---------------------------------------------------------------------------
# Invalid status fails
# ---------------------------------------------------------------------------

class TestInvalidStatus:
    def test_missing_status(self):
        with pytest.raises(ValueError, match="invalid status"):
            assert_guard_report_keys({"action": "submit"})

    def test_unknown_status(self):
        with pytest.raises(ValueError, match="invalid status"):
            assert_guard_report_keys(_ok_report(status="PENDING"))

    def test_none_status(self):
        with pytest.raises(ValueError, match="invalid status"):
            assert_guard_report_keys(_ok_report(status=None))


# ---------------------------------------------------------------------------
# Invalid types fail
# ---------------------------------------------------------------------------

class TestInvalidTypes:
    def test_not_a_dict(self):
        with pytest.raises(ValueError, match="must be dict"):
            assert_guard_report_keys("not a dict")

    def test_action_not_str(self):
        with pytest.raises(ValueError, match="action must be str"):
            validate_guard_report(_ok_report(action=123))

    def test_env_overrides_not_dict(self):
        with pytest.raises(ValueError, match="env_overrides must be dict"):
            validate_guard_report(_ok_report(env_overrides="nope"))

    def test_mode_not_str(self):
        with pytest.raises(ValueError, match="mode must be str"):
            validate_guard_report(_ok_report(mode=42))

    def test_layer0_not_bool(self):
        with pytest.raises(ValueError, match="layer0_blocked must be bool"):
            validate_guard_report(_ok_report(layer0_blocked=1))

    def test_layer1_not_bool(self):
        with pytest.raises(ValueError, match="layer1_capability must be bool"):
            validate_guard_report(_ok_report(layer1_capability="yes"))

    def test_blocked_reason_not_str(self):
        with pytest.raises(ValueError, match="reason must be str"):
            validate_guard_report(_blocked_report(reason=42))

    def test_blocked_symbol_not_str(self):
        with pytest.raises(ValueError, match="symbol must be str"):
            validate_guard_report(_blocked_report(symbol=123))


# ---------------------------------------------------------------------------
# Extra keys tolerated
# ---------------------------------------------------------------------------

class TestExtraKeys:
    def test_extra_keys_ok(self):
        r = _ok_report(extra_field="tolerated")
        assert_guard_report_keys(r)
        validate_guard_report(r)

    def test_extra_keys_blocked(self):
        r = _blocked_report(extra_field="tolerated")
        assert_guard_report_keys(r)
        validate_guard_report(r)


# ---------------------------------------------------------------------------
# Summary shape stable
# ---------------------------------------------------------------------------

class TestSummary:
    def test_ok_summary_keys(self):
        s = build_guard_report_summary(_ok_report())
        assert set(s.keys()) == {"status", "action", "mode", "all_layers_pass"}

    def test_blocked_summary_keys(self):
        s = build_guard_report_summary(_blocked_report())
        assert set(s.keys()) == {"status", "action", "reason"}

    def test_ok_all_layers_pass_true(self):
        s = build_guard_report_summary(_ok_report(
            layer0_blocked=False,
            layer1_capability=True,
            layer2_cli_allow=True,
            layer3_env_unlock=True,
            layer4_manual_confirm=True,
            layer5_symbol_ok=True,
        ))
        assert s["all_layers_pass"] is True

    def test_ok_all_layers_pass_false(self):
        s = build_guard_report_summary(_ok_report(layer0_blocked=True))
        assert s["all_layers_pass"] is False

    def test_summary_missing_report_fails(self):
        with pytest.raises(ValueError, match="invalid status"):
            build_guard_report_summary({})


# ---------------------------------------------------------------------------
# Empty / malformed
# ---------------------------------------------------------------------------

class TestEmptyMalformed:
    def test_empty_report_fails(self):
        with pytest.raises(ValueError):
            assert_guard_report_keys({})

    def test_empty_env_overrides_fails(self):
        with pytest.raises(ValueError, match="env_overrides must be dict"):
            validate_guard_report(_ok_report(env_overrides=None))
