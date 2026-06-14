"""Integration test: readonly suite depth review."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_scope_audit.suite_depth_review import (
    create_review, count_by_rating
)


def test_create_review():
    review = create_review()
    assert review.review_id.startswith("SDR_")
    assert len(review.items) == 6


def test_no_needs_followup():
    review = create_review()
    by_rating = count_by_rating(review)
    assert by_rating.get("NEEDS_FOLLOWUP", 0) == 0


def test_all_have_steps_match():
    review = create_review()
    for item in review.items:
        assert item.observed_steps == item.expected_steps


def test_rating_distribution():
    review = create_review()
    by_rating = count_by_rating(review)
    assert by_rating.get("ACCEPTABLE", 0) >= 3
    assert by_rating.get("SIMPLIFIED_ACCEPTABLE", 0) >= 3


def test_render_report():
    from src.runtime_integrations.testnet_readonly_scope_audit.suite_depth_review import render_report
    review = create_review()
    report = render_report(review)
    assert "READONLY_SUITE_DEPTH_REVIEW_READY" in report
