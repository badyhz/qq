"""Integration test: external testnet adapter spec."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_adapter_spec.external_adapter_spec import get_sections
from src.runtime_integrations.testnet_adapter_spec.external_adapter_spec_validator import validate_spec


def test_adapter_spec_sections_present():
    sections = get_sections()
    assert len(sections) >= 15


def test_adapter_spec_no_real_endpoints():
    sections = get_sections()
    for s in sections:
        if "testnet.binance.vision" in s.content:
            assert "no" in s.content.lower() or "not" in s.content.lower()


def test_adapter_spec_validator_passes():
    sections = get_sections()
    checks = validate_spec(sections)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)


def test_adapter_spec_submit_locked():
    sections = get_sections()
    content = " ".join(s.content for s in sections)
    assert "locked" in content.lower() or "not allowed" in content.lower()
