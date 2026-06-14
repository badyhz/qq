"""Integration test: readonly safety boundary summary."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_checkpoint.safety_boundary_summary import create_summary


def test_summary_ready():
    summary = create_summary()
    assert "READONLY_SAFETY_BOUNDARY_SUMMARY_READY" in summary.final_verdict


def test_all_boundaries_locked():
    summary = create_summary()
    assert summary.all_locked is True
    assert all(b.locked for b in summary.boundaries)


def test_boundary_count():
    summary = create_summary()
    assert len(summary.boundaries) >= 9


def test_real_network_not_allowed():
    summary = create_summary()
    names = [b.boundary_name for b in summary.boundaries]
    assert "REAL_NETWORK_NOT_ALLOWED" in names


def test_submit_not_allowed():
    summary = create_summary()
    names = [b.boundary_name for b in summary.boundaries]
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in names


def test_real_trading_not_allowed():
    summary = create_summary()
    names = [b.boundary_name for b in summary.boundaries]
    assert "REAL_TRADING_NOT_ALLOWED" in names


def test_chain_status():
    summary = create_summary()
    assert "completed" in summary.chain_status
    assert summary.real_readonly_network_status == "not started"
    assert summary.real_testnet_submit_status == "not started"
    assert summary.production_trading_status == "not started"
