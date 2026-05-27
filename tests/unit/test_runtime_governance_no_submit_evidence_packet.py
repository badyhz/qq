"""Tests for runtime governance no-submit evidence packet."""

from __future__ import annotations

import pytest

from core.runtime_governance_no_submit_evidence_packet import (
    RuntimeGovernanceNoSubmitEvidence,
    build_runtime_governance_no_submit_evidence_packet,
    no_submit_evidence_to_dict,
    no_submit_evidence_to_markdown,
)


@pytest.fixture
def evidence_packet():
    return build_runtime_governance_no_submit_evidence_packet()


def test_all_components_no_submit(evidence_packet):
    assert all(e.no_submit for e in evidence_packet)


def test_all_components_no_network(evidence_packet):
    assert all(e.no_network for e in evidence_packet)


def test_all_components_deterministic(evidence_packet):
    assert all(e.deterministic for e in evidence_packet)


def test_exactly_18_components(evidence_packet):
    assert len(evidence_packet) == 18


def test_markdown_deterministic(evidence_packet):
    md1 = no_submit_evidence_to_markdown(evidence_packet)
    md2 = no_submit_evidence_to_markdown(evidence_packet)
    assert md1 == md2


def test_to_dict_roundtrip(evidence_packet):
    dicts = no_submit_evidence_to_dict(evidence_packet)
    assert len(dicts) == 18
    assert all(d["no_submit"] for d in dicts)
    assert all(d["no_network"] for d in dicts)


def test_component_ids_match_t794_t811(evidence_packet):
    ids = [e.component.split(":")[0] for e in evidence_packet]
    expected = [f"T{n}" for n in range(794, 812)]
    assert ids == expected
