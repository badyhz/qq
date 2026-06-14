"""Integration test: threat model security review."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_adapter_spec.threat_model_security_review import get_threats, render_report


def test_threats_present():
    threats = get_threats()
    assert len(threats) >= 15


def test_threats_categories():
    threats = get_threats()
    categories = {t.category for t in threats}
    assert "credential_leakage" in categories
    assert "permission_overreach" in categories


def test_threats_report_flags():
    threats = get_threats()
    report = render_report(threats)
    assert "THREAT_MODEL_SECURITY_REVIEW_READY" in report
    assert "TESTNET_SUBMIT_NOT_ALLOWED" in report


def test_threats_statuses():
    threats = get_threats()
    for t in threats:
        assert t.status in ("DESIGNED", "MITIGATED", "ACCEPTED", "OPEN")
