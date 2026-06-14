"""Integration test: evidence browser."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_review.evidence_browser import (
    browse_evidence, search_evidence, categorize_evidence
)
from src.runtime_integrations.testnet_mock_replay.mock_field_test_evidence_bundle import create_bundle


def _make_bundle_dict() -> dict:
    return create_bundle(13, 13, 0).to_dict()


def test_browse_all():
    result = browse_evidence(_make_bundle_dict())
    assert result.total_items == 10
    assert len(result.matched_items) == 10


def test_browse_with_category_filter():
    result = browse_evidence(_make_bundle_dict(), [{"category": "safety_report"}])
    assert len(result.matched_items) >= 1
    for item in result.matched_items:
        assert item.get("category") == "safety_report"


def test_browse_with_keyword_filter():
    result = browse_evidence(_make_bundle_dict(), [{"keyword": "MOCK"}])
    assert len(result.matched_items) >= 1


def test_search_evidence():
    items = search_evidence(_make_bundle_dict(), "vault")
    assert len(items) >= 1


def test_categorize_evidence():
    cats = categorize_evidence(_make_bundle_dict())
    assert len(cats) >= 5
    assert "safety" in cats or "limitations" in cats
