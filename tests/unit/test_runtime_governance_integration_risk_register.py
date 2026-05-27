"""Tests for runtime governance integration risk register."""

from __future__ import annotations

import pytest

from core.runtime_governance_integration_risk_register import (
    RuntimeGovernanceIntegrationRisk,
    build_runtime_governance_integration_risk_register,
    risk_register_to_dict,
    risk_register_to_markdown,
    summarize_risk_register,
)


class TestBuildRiskRegister:
    def test_returns_eight_risks(self):
        register = build_runtime_governance_integration_risk_register()
        assert len(register) == 8

    def test_all_risk_ids_unique(self):
        register = build_runtime_governance_integration_risk_register()
        ids = [r.risk_id for r in register]
        assert len(ids) == len(set(ids))

    def test_all_risks_are_frozen(self):
        register = build_runtime_governance_integration_risk_register()
        for r in register:
            assert isinstance(r, RuntimeGovernanceIntegrationRisk)
            with pytest.raises(AttributeError):
                r.status = "mitigated"  # type: ignore[misc]

    def test_all_statuses_open(self):
        register = build_runtime_governance_integration_risk_register()
        for r in register:
            assert r.status == "open"

    def test_all_mitigations_non_empty(self):
        register = build_runtime_governance_integration_risk_register()
        for r in register:
            assert r.mitigation, f"{r.risk_id} has empty mitigation"

    def test_severity_values_valid(self):
        valid = {"low", "medium", "high", "critical"}
        register = build_runtime_governance_integration_risk_register()
        for r in register:
            assert r.severity in valid, f"{r.risk_id} invalid severity: {r.severity}"

    def test_likelihood_values_valid(self):
        valid = {"low", "medium", "high"}
        register = build_runtime_governance_integration_risk_register()
        for r in register:
            assert r.likelihood in valid, f"{r.risk_id} invalid likelihood: {r.likelihood}"

    def test_expected_risk_ids_present(self):
        expected = {
            "accidental_submit",
            "network_permission_leak",
            "stale_governance_verdict",
            "missing_manual_approval",
            "planner_bypass",
            "secret_exposure",
            "untracked_file_io",
            "nondeterministic_evidence",
        }
        register = build_runtime_governance_integration_risk_register()
        actual = {r.risk_id for r in register}
        assert actual == expected

    def test_accidental_submit_critical_high(self):
        register = build_runtime_governance_integration_risk_register()
        r = next(x for x in register if x.risk_id == "accidental_submit")
        assert r.severity == "critical"
        assert r.likelihood == "high"

    def test_nondeterministic_evidence_low_medium(self):
        register = build_runtime_governance_integration_risk_register()
        r = next(x for x in register if x.risk_id == "nondeterministic_evidence")
        assert r.severity == "low"
        assert r.likelihood == "medium"


class TestRiskRegisterToDict:
    def test_returns_list_of_dicts(self):
        register = build_runtime_governance_integration_risk_register()
        result = risk_register_to_dict(register)
        assert isinstance(result, list)
        assert len(result) == 8
        for d in result:
            assert isinstance(d, dict)

    def test_dict_has_expected_keys(self):
        register = build_runtime_governance_integration_risk_register()
        result = risk_register_to_dict(register)
        expected_keys = {"risk_id", "title", "severity", "likelihood", "mitigation", "status"}
        for d in result:
            assert set(d.keys()) == expected_keys

    def test_dict_values_match_dataclass(self):
        register = build_runtime_governance_integration_risk_register()
        result = risk_register_to_dict(register)
        for orig, d in zip(register, result):
            assert d["risk_id"] == orig.risk_id
            assert d["title"] == orig.title
            assert d["severity"] == orig.severity
            assert d["likelihood"] == orig.likelihood
            assert d["mitigation"] == orig.mitigation
            assert d["status"] == orig.status

    def test_empty_register(self):
        result = risk_register_to_dict([])
        assert result == []


class TestRiskRegisterToMarkdown:
    def test_contains_header(self):
        register = build_runtime_governance_integration_risk_register()
        md = risk_register_to_markdown(register)
        assert "# Runtime Governance Integration Risk Register" in md

    def test_contains_table(self):
        register = build_runtime_governance_integration_risk_register()
        md = risk_register_to_markdown(register)
        assert "| Risk ID |" in md
        assert "|---------" in md

    def test_contains_all_risk_ids(self):
        register = build_runtime_governance_integration_risk_register()
        md = risk_register_to_markdown(register)
        for r in register:
            assert r.risk_id in md

    def test_contains_mitigations(self):
        register = build_runtime_governance_integration_risk_register()
        md = risk_register_to_markdown(register)
        for r in register:
            assert r.mitigation in md

    def test_empty_register(self):
        md = risk_register_to_markdown([])
        assert "# Runtime Governance Integration Risk Register" in md


class TestSummarizeRiskRegister:
    def test_total_count(self):
        register = build_runtime_governance_integration_risk_register()
        summary = summarize_risk_register(register)
        assert summary["total"] == 8

    def test_by_severity_keys(self):
        register = build_runtime_governance_integration_risk_register()
        summary = summarize_risk_register(register)
        assert "low" in summary["by_severity"]
        assert "medium" in summary["by_severity"]
        assert "high" in summary["by_severity"]
        assert "critical" in summary["by_severity"]

    def test_by_likelihood_keys(self):
        register = build_runtime_governance_integration_risk_register()
        summary = summarize_risk_register(register)
        assert "medium" in summary["by_likelihood"]
        assert "high" in summary["by_likelihood"]

    def test_by_status_keys(self):
        register = build_runtime_governance_integration_risk_register()
        summary = summarize_risk_register(register)
        assert summary["by_status"] == {"open": 8}

    def test_severity_sums_to_total(self):
        register = build_runtime_governance_integration_risk_register()
        summary = summarize_risk_register(register)
        assert sum(summary["by_severity"].values()) == summary["total"]

    def test_likelihood_sums_to_total(self):
        register = build_runtime_governance_integration_risk_register()
        summary = summarize_risk_register(register)
        assert sum(summary["by_likelihood"].values()) == summary["total"]

    def test_empty_register(self):
        summary = summarize_risk_register([])
        assert summary["total"] == 0
        assert summary["by_severity"] == {}
        assert summary["by_likelihood"] == {}
        assert summary["by_status"] == {}
