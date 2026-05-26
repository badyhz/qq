"""Tests for Workflow Status."""
from __future__ import annotations

import importlib
import sys

import pytest

from core.execution_guards import ExecutionGuardError

_FAKE_ARGV = ["workflow_status"]


def test_import_safe():
    mod = importlib.import_module("scripts.workflow_status")
    assert hasattr(mod, "main")
    assert hasattr(mod, "render_workflow")


def test_no_high_risk_imports():
    source = open("scripts/workflow_status.py", encoding="utf-8").read()
    for forbidden in [
        "binance_connector",
        "binance_http",
        "binance_testnet",
        "broker_connector",
        "live_runner",
    ]:
        assert forbidden not in source, f"forbidden import: {forbidden}"


def test_default_dry_run_allowed(monkeypatch):
    monkeypatch.delenv("QQ_RUNTIME_MODE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.workflow_status import main
    with pytest.raises(ValueError):
        main()


def test_dry_run_all(monkeypatch, capsys):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--all"])
    from scripts.workflow_status import main
    main()
    output = capsys.readouterr().out
    assert "GUARD_BATCH" in output
    assert "DOCS_SYNC" in output
    assert "CLOSEOUT" in output


def test_dry_run_single(monkeypatch, capsys):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--workflow", "guard_batch"])
    from scripts.workflow_status import main
    main()
    output = capsys.readouterr().out
    assert "GUARD_BATCH" in output
    assert "Progress:" in output


def test_live_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "live")
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--all"])
    from scripts.workflow_status import main
    with pytest.raises(ExecutionGuardError, match="live"):
        main()


def test_render_state():
    from scripts.workflow_status import render_state
    assert "[PASS]" in render_state("COMPLETED")
    assert "[....]" in render_state("RUNNING")
    assert "[WAIT]" in render_state("READY")
