"""Integration test: testnet read-only checkpoint suite."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_checkpoint.checkpoint_summary import create_summary
from src.runtime_integrations.testnet_readonly_checkpoint.tag_chain_manifest import create_manifest
from src.runtime_integrations.testnet_readonly_checkpoint.safety_boundary_summary import create_summary as create_boundary_summary
from src.runtime_integrations.testnet_readonly_checkpoint.next_stage_decision_pack import create_pack
from src.runtime_integrations.testnet_readonly_checkpoint.checkpoint_safety_regression import run_regression


def test_checkpoint_summary_ready():
    summary = create_summary()
    assert summary.total_stages >= 13
    assert summary.real_network_enabled is False


def test_tag_chain_ready():
    manifest = create_manifest()
    assert manifest.all_present is True


def test_safety_boundary_ready():
    summary = create_boundary_summary()
    assert summary.all_locked is True


def test_next_stage_ready():
    pack = create_pack()
    assert pack.recommended_next == "OPTION_D_ARCHIVE_CURRENT_CHAIN_AND_WAIT_FOR_HUMAN_APPROVAL"


def test_safety_regression_clean():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Safety regression failures: {[i.check_id for i in failed]}"
