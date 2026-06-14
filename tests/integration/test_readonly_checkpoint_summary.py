"""Integration test: readonly checkpoint summary."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_checkpoint.checkpoint_summary import create_summary


def test_checkpoint_ready():
    summary = create_summary()
    assert "READONLY_CHECKPOINT_SUMMARY_READY" in summary.final_verdict


def test_stage_count():
    summary = create_summary()
    assert summary.total_stages >= 13


def test_latest_tag_present():
    summary = create_summary()
    assert summary.latest_tag == "testnet-readonly-prd-compliance-correction-complete"


def test_no_real_network():
    summary = create_summary()
    assert summary.real_network_enabled is False


def test_no_submit():
    summary = create_summary()
    assert summary.testnet_submit_allowed is False


def test_no_real_trading():
    summary = create_summary()
    assert summary.real_trading_allowed is False


def test_all_stages_complete():
    summary = create_summary()
    assert all(s.current_status == "COMPLETE" for s in summary.stages)
