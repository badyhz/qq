"""Integration test: mock field-test evidence bundle."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_mock_replay.mock_field_test_evidence_bundle import create_bundle, render_report


def test_bundle_created():
    bundle = create_bundle(13, 13, 0)
    assert bundle.bundle_id.startswith("BUNDLE_")
    assert len(bundle.items) >= 10


def test_bundle_has_limitations():
    bundle = create_bundle(13, 13, 0)
    report = render_report(bundle)
    assert "THIS_IS_MOCK_EVIDENCE_ONLY" in report
    assert "REAL_TESTNET_SUBMIT_NOT_ALLOWED" in report
    assert "REAL_TRADING_NOT_ALLOWED" in report


def test_bundle_report_flags():
    bundle = create_bundle(13, 13, 0)
    report = render_report(bundle)
    assert "MOCK_FIELD_TEST_EVIDENCE_BUNDLE_READY" in report
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in report


def test_bundle_has_safety_report():
    bundle = create_bundle(13, 13, 0)
    categories = {i.category for i in bundle.items}
    assert "safety_report" in categories
    assert "limitations" in categories
