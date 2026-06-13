"""Integration test: enablement readiness review."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_enablement.enablement_readiness_review import run_review
from src.runtime_integrations.testnet_enablement.enablement_readiness_policy import get_criteria


def test_readiness_review_submit_not_allowed():
    review = run_review()
    assert review.submit_allowed is False
    assert review.testnet_submit_allowed is False


def test_readiness_review_all_criteria_met():
    review = run_review()
    assert review.review_ready is True
    assert len(review.criteria_met) >= 11


def test_readiness_policy_criteria_count():
    criteria = get_criteria()
    assert len(criteria) >= 11
    for c in criteria:
        assert c.status in ("MET", "DOCUMENTED", "STUB_ONLY", "SIMULATED_ONLY")


def test_readiness_review_no_forbidden_status():
    review = run_review()
    forbidden = ("TESTNET_SUBMIT_ALLOWED", "REAL_SUBMIT_ALLOWED", "LIVE_TRADING_READY")
    review_dict = review.to_dict()
    for key, val in review_dict.items():
        if isinstance(val, str):
            for f in forbidden:
                assert f not in val, f"Forbidden status {f} in {key}"
