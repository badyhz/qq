"""Tests for T847 runtime governance read-only threat model."""

from core.runtime_governance_readonly_threat_model import (
    RuntimeGovernanceReadOnlyThreat,
    build_readonly_threat_model,
    readonly_threat_model_to_dict,
    readonly_threat_model_to_markdown,
    summarize_readonly_threat_model,
)


def test_five_threats():
    threats = build_readonly_threat_model()
    assert len(threats) == 5


def test_critical_threats_present():
    threats = build_readonly_threat_model()
    severities = {t.severity for t in threats}
    assert "critical" in severities


def test_all_mitigations_non_empty():
    threats = build_readonly_threat_model()
    for t in threats:
        assert t.mitigation, f"Empty mitigation for {t.threat_id}"


def test_deterministic():
    a = build_readonly_threat_model()
    b = build_readonly_threat_model()
    assert a == b


def test_to_dict_returns_list_of_dicts():
    threats = build_readonly_threat_model()
    result = readonly_threat_model_to_dict(threats)
    assert isinstance(result, list)
    assert all(isinstance(d, dict) for d in result)
    assert len(result) == 5


def test_markdown_contains_threat_id():
    threats = build_readonly_threat_model()
    md = readonly_threat_model_to_markdown(threats)
    for t in threats:
        assert t.threat_id in md


def test_summarize_returns_total_five():
    threats = build_readonly_threat_model()
    summary = summarize_readonly_threat_model(threats)
    assert summary["total"] == 5
