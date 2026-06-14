"""Integration test: read-only discovery design."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_discovery.discovery_design import create_design


def test_create_design():
    design = create_design()
    assert design.discovery_id.startswith("DSC_")
    assert design.final_decision == "READ_ONLY_TESTNET_DISCOVERY_DESIGN_READY"


def test_allowed_methods():
    design = create_design()
    assert len(design.allowed_methods) == 5
    for m in design.allowed_methods:
        assert "DRY_RUN" in m


def test_prohibited_methods():
    design = create_design()
    assert "SUBMIT_ORDER" in design.prohibited_methods
    assert "CANCEL_ORDER" in design.prohibited_methods
    assert "WITHDRAW" in design.prohibited_methods


def test_no_real_methods():
    design = create_design()
    for m in design.allowed_methods:
        assert "REAL" not in m or "DRY_RUN" in m


def test_render_report():
    from src.runtime_integrations.testnet_readonly_discovery.discovery_design import render_report
    design = create_design()
    report = render_report(design)
    assert "READ_ONLY_TESTNET_DISCOVERY_DESIGN_READY" in report
    assert "REAL_NETWORK_NOT_ALLOWED" in report
