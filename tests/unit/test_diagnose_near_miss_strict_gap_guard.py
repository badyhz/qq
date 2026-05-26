from __future__ import annotations
import importlib
import sys
import pytest
from core.execution_guards import ExecutionGuardError

_FAKE_ARGV = ["diagnose_near_miss_strict_gap"]

def test_import_safe():
    mod = importlib.import_module("scripts.diagnose_near_miss_strict_gap")
    assert hasattr(mod, "main")
    assert hasattr(mod, "diagnose_near_miss_strict_gap")

def test_no_high_risk_imports():
    source = open("scripts/diagnose_near_miss_strict_gap.py", encoding="utf-8").read()
    for forbidden in ["binance_connector", "binance_http", "binance_testnet", "broker_connector", "live_runner"]:
        assert forbidden not in source, f"forbidden import: {forbidden}"

def test_default_dry_run_allowed(monkeypatch):
    monkeypatch.delenv("QQ_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.diagnose_near_miss_strict_gap import main
    with pytest.raises(ValueError):
        main()

def test_dry_run_mode_allowed(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.diagnose_near_miss_strict_gap import main
    main()

def test_live_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "live")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.diagnose_near_miss_strict_gap import main
    with pytest.raises(ExecutionGuardError, match="live"):
        main()

def test_unknown_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "bogus")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.diagnose_near_miss_strict_gap import main
    with pytest.raises(ValueError):
        main()
