"""Integration test: exchange response fixtures."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_transport.exchange_response_fixtures import get_fixtures, render_report


def test_fixtures_present():
    fixtures = get_fixtures()
    assert len(fixtures) >= 11


def test_fixture_categories():
    fixtures = get_fixtures()
    categories = {f.category for f in fixtures}
    assert "submit" in categories
    assert "cancel" in categories
    assert "reconcile" in categories
    assert "error" in categories


def test_fixture_status_codes():
    fixtures = get_fixtures()
    for f in fixtures:
        assert 100 <= f.status_code <= 599


def test_report_flags():
    fixtures = get_fixtures()
    report = render_report(fixtures)
    assert "MOCK_ONLY" in report
    assert "submit_allowed=false" in report
    assert "EXCHANGE_RESPONSE_FIXTURE_SCHEMA_READY" in report
