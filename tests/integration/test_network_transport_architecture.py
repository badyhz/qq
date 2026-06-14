"""Integration test: network transport architecture."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_adapter_spec.network_transport_architecture import get_sections, render_report
from src.runtime_integrations.testnet_adapter_spec.network_transport_validator import validate_architecture


def test_transport_sections_present():
    sections = get_sections()
    assert len(sections) >= 14


def test_transport_report_flags():
    sections = get_sections()
    report = render_report(sections)
    assert "ARCHITECTURE_ONLY" in report
    assert "network_client_implemented=false" in report
    assert "network_called=false" in report
    assert "submit_allowed=false" in report


def test_transport_validator_passes():
    sections = get_sections()
    report = render_report(sections)
    checks = validate_architecture(report)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)
