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
    from scripts import verify_engineering_closeout_state as mod

    _fake_hash = "abc1234def5678"
    _calls: list[int] = [0]

    def _fake_run_cmd(args: list[str]) -> tuple[int, str]:
        _calls[0] += 1
        cmd = " ".join(args)
        if "--is-inside-work-tree" in cmd:
            return 0, "true"
        if "log --oneline -1" in cmd:
            return 0, "abc1234 chore: fake"
        if "rev-parse" in cmd and "phase2-complete" in cmd:
            return 0, _fake_hash
        if "rev-parse HEAD" in cmd:
            return 0, _fake_hash
        if "status --short" in cmd:
            return 0, "?? some_untracked_file.py"
        if "diff --cached --name-only" in cmd:
            return 0, ""
        if "show --stat" in cmd:
            return 0, " some_file.py"
        return 0, ""

    monkeypatch.setattr(mod, "run_cmd", _fake_run_cmd)
    with pytest.raises(SystemExit) as exc_info:
        mod.main()
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
