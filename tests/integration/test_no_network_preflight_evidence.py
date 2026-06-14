"""Integration test: no-network preflight evidence."""
from __future__ import annotations
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from src.runtime_integrations.testnet_readonly_preapproval.no_network_preflight_evidence import (
    create_evidence, count_passed, count_active_blockers
)


def test_create_evidence():
    evidence = create_evidence()
    assert evidence.preflight_id.startswith("PFE_")
    assert len(evidence.items) >= 8


def test_all_passed():
    evidence = create_evidence()
    assert count_passed(evidence) == len(evidence.items)


def test_has_active_blockers():
    evidence = create_evidence()
    assert count_active_blockers(evidence) >= 1


def test_has_network_checks():
    evidence = create_evidence()
    network = [i for i in evidence.items if i.category == "network"]
    assert len(network) >= 2


def test_has_credential_checks():
    evidence = create_evidence()
    creds = [i for i in evidence.items if i.category == "credential"]
    assert len(creds) >= 2


def test_render_report():
    from src.runtime_integrations.testnet_readonly_preapproval.no_network_preflight_evidence import render_report
    evidence = create_evidence()
    report = render_report(evidence)
    assert "NO_NETWORK_PREFLIGHT_EVIDENCE_READY" in report
    assert "REAL_NETWORK_NOT_ALLOWED" in report
