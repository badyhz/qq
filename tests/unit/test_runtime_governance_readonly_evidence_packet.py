"""Tests for T839: Runtime governance read-only evidence packet."""
from core.runtime_governance_readonly_evidence_packet import (
    RuntimeGovernanceReadOnlyEvidence,
    build_readonly_evidence_packet,
    readonly_evidence_packet_to_dict,
    readonly_evidence_packet_to_markdown,
)


def test_evidence_packet_has_13_items():
    packet = build_readonly_evidence_packet()
    assert len(packet) == 13


def test_all_verdicts_pass():
    packet = build_readonly_evidence_packet()
    for e in packet:
        assert e.verdict == "PASS", f"{e.component} verdict={e.verdict}"


def test_no_dangerous_permissions():
    packet = build_readonly_evidence_packet()
    for e in packet:
        assert e.read_only is True
        assert e.no_network is True
        assert e.no_write is True
        assert e.no_order is True
        assert e.no_secret is True
        assert e.deterministic is True


def test_deterministic():
    a = build_readonly_evidence_packet()
    b = build_readonly_evidence_packet()
    assert a == b


def test_to_dict_returns_list_of_dicts():
    packet = build_readonly_evidence_packet()
    dicts = readonly_evidence_packet_to_dict(packet)
    assert isinstance(dicts, list)
    assert len(dicts) == 13
    for d in dicts:
        assert isinstance(d, dict)
        assert "component" in d
        assert "verdict" in d


def test_markdown_contains_header():
    packet = build_readonly_evidence_packet()
    md = readonly_evidence_packet_to_markdown(packet)
    assert "Runtime Governance Read-Only Evidence Packet" in md
    assert "| Component |" in md


def test_dataclass_frozen():
    e = RuntimeGovernanceReadOnlyEvidence(
        component="x",
        read_only=True,
        no_network=True,
        no_write=True,
        no_order=True,
        no_secret=True,
        deterministic=True,
        verdict="PASS",
    )
    try:
        e.component = "y"  # type: ignore[misc]
        assert False, "Should be frozen"
    except AttributeError:
        pass
