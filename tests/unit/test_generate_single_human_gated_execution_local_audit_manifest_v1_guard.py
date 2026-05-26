from __future__ import annotations
import importlib
import sys
import pytest
from core.execution_guards import ExecutionGuardError

_FAKE_ARGV = [
    "generate_single_human_gated_execution_local_audit_manifest_v1",
    "--wrapper-phase-json", "x.json",
    "--final-safety-gate-json", "x.json",
    "--wrapper-artifact-json", "x.json",
    "--wrapper-invariant-json", "x.json",
    "--command-preview-json", "x.json",
]

def test_import_safe():
    mod = importlib.import_module("scripts.generate_single_human_gated_execution_local_audit_manifest_v1")
    assert hasattr(mod, "main")
    assert hasattr(mod, "generate_manifest")

def test_no_high_risk_imports():
    source = open("scripts/generate_single_human_gated_execution_local_audit_manifest_v1.py", encoding="utf-8").read()
    for forbidden in ["binance_connector", "binance_http", "binance_testnet", "broker_connector", "live_runner"]:
        assert forbidden not in source, f"forbidden import: {forbidden}"

def test_default_dry_run_allowed(monkeypatch):
    monkeypatch.delenv("QQ_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.generate_single_human_gated_execution_local_audit_manifest_v1 import main
    with pytest.raises(ValueError):
        main()

def test_dry_run_mode_allowed(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.generate_single_human_gated_execution_local_audit_manifest_v1 import main
    main()

def test_live_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "live")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.generate_single_human_gated_execution_local_audit_manifest_v1 import main
    with pytest.raises(ExecutionGuardError, match="live"):
        main()

def test_unknown_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "bogus")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.generate_single_human_gated_execution_local_audit_manifest_v1 import main
    with pytest.raises(ValueError):
        main()
