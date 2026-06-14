"""Integration test: operator review index."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_review.operator_review_index import (
    create_index, search_artifacts, filter_by_category
)


def test_create_index():
    index = create_index()
    assert len(index.artifacts) >= 12
    assert index.index_id.startswith("IDX_")


def test_search_artifacts():
    index = create_index()
    results = search_artifacts(index, "evidence")
    assert len(results) >= 1


def test_filter_by_category():
    index = create_index()
    replay = filter_by_category(index, "replay")
    assert len(replay) >= 2
    for a in replay:
        assert a.category == "replay"


def test_filter_safety():
    index = create_index()
    safety = filter_by_category(index, "safety")
    assert len(safety) >= 1
