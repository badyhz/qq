"""Integration test: adapter plan validation."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_enablement.external_adapter_plan import get_plan_sections
from src.runtime_integrations.testnet_enablement.external_adapter_plan_validator import validate_plan


def test_adapter_plan_sections_present():
    sections = get_plan_sections()
    assert len(sections) >= 12


def test_adapter_plan_no_real_endpoints():
    sections = get_plan_sections()
    for s in sections:
        content = s.content.lower()
        assert "real" not in content or "no real" in content or "real endpoint" not in content


def test_adapter_plan_validator_passes():
    sections = get_plan_sections()
    checks = validate_plan(sections)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)


def test_adapter_plan_design_only():
    sections = get_plan_sections()
    for s in sections:
        assert s.status in ("DESIGNED", "DOCUMENTED", "PLANNED", "STUB_ONLY")
