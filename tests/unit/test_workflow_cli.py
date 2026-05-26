"""Tests for Workflow CLI."""
from __future__ import annotations

import importlib
import sys

import pytest

from core.execution_guards import ExecutionGuardError

_FAKE_ARGV = ["workflow_cli"]


def test_import_safe():
    mod = importlib.import_module("scripts.workflow_cli")
    assert hasattr(mod, "main")
    assert hasattr(mod, "mode_queue")
    assert hasattr(mod, "mode_dag")
    assert hasattr(mod, "mode_closeout")


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


def test_default_dry_run_allowed(monkeypatch):
    monkeypatch.delenv("QQ_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV)
    from scripts.workflow_cli import main

    with pytest.raises(ValueError):
        main()


def test_dry_run_mode_allowed_queue(monkeypatch, capsys):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--mode", "queue"])
    from scripts.workflow_cli import main

    main()
    output = capsys.readouterr().out
    assert "QUEUE MODE" in output


def test_dry_run_mode_allowed_dag(monkeypatch, capsys):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--mode", "dag"])
    from scripts.workflow_cli import main

    main()
    output = capsys.readouterr().out
    assert "DAG MODE" in output


def test_dry_run_mode_allowed_closeout(monkeypatch, capsys):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "dry_run")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--mode", "closeout"])
    from scripts.workflow_cli import main

    main()
    output = capsys.readouterr().out
    assert "CLOSEOUT MODE" in output


def test_live_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "live")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--mode", "queue"])
    from scripts.workflow_cli import main

    with pytest.raises(ExecutionGuardError, match="live"):
        main()


def test_unknown_mode_blocked(monkeypatch):
    monkeypatch.setenv("QQ_RUNTIME_MODE", "bogus")
    monkeypatch.delenv("QQ_REQUIRE_DRY_RUN", raising=False)
    monkeypatch.delenv("QQ_NO_LIVE", raising=False)
    monkeypatch.setattr(sys, "argv", _FAKE_ARGV + ["--mode", "queue"])
    from scripts.workflow_cli import main

    with pytest.raises(ValueError):
        main()
