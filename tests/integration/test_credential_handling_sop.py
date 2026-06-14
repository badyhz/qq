"""Integration test: credential handling SOP."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_preapproval.credential_handling_sop import create_sop


def test_create_sop():
    sop = create_sop()
    assert sop.sop_id.startswith("SOP_")
    assert len(sop.sections) >= 8


def test_has_required_sections():
    sop = create_sop()
    titles = {s.title for s in sop.sections}
    assert "Placeholder Credential Policy" in titles
    assert "Redaction Rules" in titles
    assert "Forbidden Raw Secret Patterns" in titles
    assert "Operator Prohibition List" in titles


def test_no_real_secrets():
    sop = create_sop()
    for s in sop.sections:
        content = s.content.lower()
        assert "real_api_key" not in content
        assert "real_secret" not in content


def test_render_report():
    from src.runtime_integrations.testnet_readonly_preapproval.credential_handling_sop import render_report
    sop = create_sop()
    report = render_report(sop)
    assert "CREDENTIAL_HANDLING_SOP_READY" in report
    assert "REAL_CREDENTIALS_NOT_ALLOWED" in report
    assert "RAW_SECRET_NOT_ALLOWED" in report
