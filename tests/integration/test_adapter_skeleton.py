"""Integration test: adapter skeleton."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_transport.adapter_skeleton import (
    build_order_request, validate_order_request,
    submit_order_dry_run, cancel_order_dry_run,
    reconcile_balance_dry_run, reconcile_position_dry_run,
    render_report
)


def test_build_order_request():
    req = build_order_request("BTCUSDT", "BUY", "LIMIT", "0.001", "50000.00")
    assert req.symbol == "BTCUSDT"
    assert req.side == "BUY"
    assert req.request_id.startswith("ORD_")


def test_validate_order_valid():
    req = build_order_request("BTCUSDT", "BUY", "LIMIT", "0.001", "50000.00")
    result = validate_order_request(req)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_order_invalid_symbol():
    req = build_order_request("INVALID", "BUY", "LIMIT", "0.001", "50000.00")
    result = validate_order_request(req)
    assert result["valid"] is False


def test_submit_dry_run():
    req = build_order_request("BTCUSDT", "BUY", "LIMIT", "0.001", "50000.00")
    result = submit_order_dry_run(req)
    assert result.simulated is True
    assert result.real_submit is False
    assert result.testnet_submit is False
    assert result.no_submit_enforced is True


def test_cancel_dry_run():
    result = cancel_order_dry_run("MOCK_001")
    assert result.simulated is True
    assert result.real_submit is False
    assert result.no_submit_enforced is True


def test_reconcile_dry_run():
    balance = reconcile_balance_dry_run()
    position = reconcile_position_dry_run()
    assert balance.simulated is True
    assert position.simulated is True


def test_report_flags():
    report = render_report()
    assert "DRY_RUN_MOCK_ONLY" in report
    assert "real_submit=false" in report
    assert "submit_allowed=false" in report
    assert "ADAPTER_SKELETON_NO_NETWORK_READY" in report
