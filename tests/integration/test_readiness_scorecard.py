"""Integration test: readiness scorecard."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_closeout.readiness_scorecard import (
    create_scorecard, average_score, mock_readiness, real_readiness
)


def test_create_scorecard():
    scorecard = create_scorecard()
    assert len(scorecard.dimensions) == 10
    assert scorecard.scorecard_id.startswith("RSC_")


def test_mock_readiness_high():
    scorecard = create_scorecard()
    assert mock_readiness(scorecard) >= 80


def test_real_readiness_zero():
    scorecard = create_scorecard()
    assert real_readiness(scorecard) == 0


def test_real_submit_readiness_zero():
    scorecard = create_scorecard()
    real_submit = [d for d in scorecard.dimensions if d.name == "real_submit_readiness"]
    assert len(real_submit) == 1
    assert real_submit[0].score == 0


def test_final_verdict():
    scorecard = create_scorecard()
    assert "MOCK_READY" in scorecard.final_verdict
    assert "REAL_TESTNET_NOT_READY" in scorecard.final_verdict
    assert "SUBMIT_UNLOCK_BLOCKED" in scorecard.final_verdict


def test_render_report():
    from src.runtime_integrations.testnet_mock_closeout.readiness_scorecard import render_report
    scorecard = create_scorecard()
    report = render_report(scorecard)
    assert "READINESS_SCORECARD_READY" in report
    assert "REAL_TESTNET_NOT_READY" in report
