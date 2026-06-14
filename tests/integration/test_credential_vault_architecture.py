"""Integration test: credential vault architecture."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_adapter_spec.credential_vault_architecture import get_sections, render_report
from src.runtime_integrations.testnet_adapter_spec.credential_vault_architecture_validator import validate_architecture


def test_vault_sections_present():
    sections = get_sections()
    assert len(sections) >= 17


def test_vault_report_flags():
    sections = get_sections()
    report = render_report(sections)
    assert "ARCHITECTURE_ONLY" in report
    assert "real_credentials_enabled=false" in report
    assert "env_secret_read=false" in report
    assert "submit_allowed=false" in report


def test_vault_validator_passes():
    sections = get_sections()
    report = render_report(sections)
    checks = validate_architecture(report)
    passed = sum(1 for c in checks if c.passed)
    assert passed == len(checks)


def test_vault_no_key_generation():
    sections = get_sections()
    report = render_report(sections)
    checks = validate_architecture(report)
    no_gen = [c for c in checks if c.check_id == "no_key_generation"]
    assert len(no_gen) == 1
    assert no_gen[0].passed
