from __future__ import annotations

import importlib
import sys

import pytest

from core.execution_guards import ExecutionGuardError

_FAKE_ARGV = ["verify_engineering_closeout_state"]


def test_import_safe():
    mod = importlib.import_module("scripts.verify_engineering_closeout_state")
    assert hasattr(mod, "main")
    assert hasattr(mod, "verify_engineering_closeout")


def test_no_high_risk_imports():
    """Ensure no live-trading connector imports appear in the script."""
    import re

    source = open(
        "scripts/verify_engineering_closeout_state.py", encoding="utf-8"
    ).read()
    # Strip string literals so pattern-matching strings in FROZEN_PATTERNS
    # don't trigger false positives.
    source_no_strings = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    for forbidden in [
        "binance_connector",
        "binance_http",
        "binance_testnet",
        "broker_connector",
    ]:
        assert forbidden not in source_no_strings, f"forbidden import: {forbidden}"


def test_default_dry_run_allowed(monkeypatch):
    monkeypatch.delenv("QQ_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.verify_engineering_closeout_state import main

    with pytest.raises(ValueError):
        main()


def test_dry_run_mode_allowed(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--tag", "phase2-complete"])
    from scripts.verify_engineering_closeout_state import main

    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0


def test_live_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "live")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.verify_engineering_closeout_state import main

    with pytest.raises(ExecutionGuardError, match="live"):
        main()


def test_unknown_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "bogus")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.verify_engineering_closeout_state import main

    with pytest.raises(ValueError):
        main()
