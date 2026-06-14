"""Integration test: external testnet mock closeout suite runner."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_closeout.closeout_summary import create_summary
from src.runtime_integrations.testnet_mock_closeout.gate_blocker_ledger import create_ledger
from src.runtime_integrations.testnet_mock_closeout.readiness_scorecard import create_scorecard, real_readiness, mock_readiness
from src.runtime_integrations.testnet_mock_closeout.final_no_submit_archive import create_archive
from src.runtime_integrations.testnet_mock_closeout.next_stage_prerequisite_checklist import create_checklist
from src.runtime_integrations.testnet_mock_closeout.closeout_safety_regression import run_regression


def test_closeout_summary_exists():
    summary = create_summary()
    assert summary.overall_status == "MOCK_REVIEW_CLOSEOUT_READY"


def test_gate_blocker_ledger_blocks_submit():
    ledger = create_ledger()
    assert len(ledger.blockers) >= 10
    for b in ledger.blockers:
        assert b.current_status == "BLOCKED"


def test_readiness_real_submit_zero():
    scorecard = create_scorecard()
    assert real_readiness(scorecard) == 0


def test_readiness_mock_high():
    scorecard = create_scorecard()
    assert mock_readiness(scorecard) >= 80


def test_archive_has_final_declaration():
    archive = create_archive()
    declarations = [e for e in archive.entries if e.category == "final_declaration"]
    assert len(declarations) >= 1
    assert "FINAL_NO_SUBMIT_ARCHIVE_READY" in declarations[0].content


def test_prerequisite_checklist_blocks_submit():
    checklist = create_checklist()
    assert checklist.next_stage == "READ_ONLY_TESTNET_DISCOVERY"


def test_safety_regression_clean():
    items = run_regression()
    failed = [i for i in items if not i.passed]
    assert len(failed) == 0, f"Safety regression failures: {[i.check_id for i in failed]}"
