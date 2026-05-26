"""Tests for Workflow CLI Runtime Integration."""
from __future__ import annotations

import importlib
import sys

import pytest

from core.execution_guards import ExecutionGuardError

_FAKE_ARGV = ["workflow_cli"]


def test_import_safe():
    mod = importlib.import_module("scripts.workflow_cli")
    assert hasattr(mod, "main")


def test_no_high_risk_imports():
    source = open("scripts/workflow_cli.py", encoding="utf-8").read()
    for forbidden in [
        "binance_connector",
        "binance_http",
        "binance_testnet",
        "broker_connector",
        "live_runner",
    ]:
        assert forbidden not in source, f"forbidden import: {forbidden}"


def test_dry_run_workflow_safe_readonly(monkeypatch, capsys):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--workflow", "safe_readonly_audit"])
    from scripts.workflow_cli import main
    main()
    output = capsys.readouterr().out
    assert "SAFE_READONLY_AUDIT" in output


def test_dry_run_workflow_guard_injection(monkeypatch, capsys):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--workflow", "guard_injection_batch"])
    from scripts.workflow_cli import main
    main()
    output = capsys.readouterr().out
    assert "GUARD_INJECTION_BATCH" in output


def test_dry_run_workflow_closeout(monkeypatch, capsys):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--workflow", "engineering_closeout"])
    from scripts.workflow_cli import main
    main()
    output = capsys.readouterr().out
    assert "ENGINEERING_CLOSEOUT" in output


def test_live_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "live")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--workflow", "safe_readonly_audit"])
    from scripts.workflow_cli import main
    with pytest.raises(ExecutionGuardError, match="live"):
        main()


def test_unknown_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "bogus")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--workflow", "safe_readonly_audit"])
    from scripts.workflow_cli import main
    with pytest.raises(ValueError):
        main()
