"""Tests for T901 — PRD 500-backlog domain catalog.

Deterministic. No I/O. No timestamps. No random.
"""

import pytest

from core.prd_500_backlog_domain_catalog import (
    Prd500BacklogDomain,
    build_prd_500_backlog_domain_catalog,
    domain_to_dict,
    domain_to_markdown,
    domains_to_dict,
    domains_to_markdown,
    summarize_domain_catalog,
)

_CATALOG = build_prd_500_backlog_domain_catalog()


class TestDomainCatalog:
    def test_all_domains_present(self):
        ids = [d.domain_id for d in _CATALOG]
        assert len(ids) == 10
        assert len(set(ids)) == 10, "duplicate domain_id"
        for prefix in [
            "D01", "D02", "D03", "D04", "D05",
            "D06", "D07", "D08", "D09", "D10",
        ]:
            assert any(did.startswith(prefix) for did in ids), f"missing {prefix}"

    def test_total_target_count(self):
        total = sum(d.target_task_count for d in _CATALOG)
        assert total >= 500, f"total {total} < 500"

    def test_frozen_live_domain(self):
        d08 = next(d for d in _CATALOG if d.domain_id.startswith("D08"))
        assert d08.default_risk_level == "FROZEN"
        assert d08.human_review_required is True
        assert d08.target_task_count == 40

    def test_forbidden_patterns(self):
        required = {"secrets", "credentials", "api_keys", ".env"}
        for d in _CATALOG:
            present = set(d.forbidden_file_patterns)
            assert required.issubset(present), (
                f"{d.domain_id} missing forbidden: {required - present}"
            )

    def test_d08_extra_forbidden(self):
        d08 = next(d for d in _CATALOG if d.domain_id.startswith("D08"))
        extra = {"live trading", "real order placement", "exchange client", "planner autonomous"}
        assert extra.issubset(set(d08.forbidden_file_patterns))

    def test_deterministic_markdown(self):
        md1 = domains_to_markdown(_CATALOG)
        md2 = domains_to_markdown(_CATALOG)
        assert md1 == md2

    def test_no_live_authorization(self):
        for d in _CATALOG:
            blob = domain_to_markdown(d).lower()
            assert "authorized for live" not in blob, (
                f"{d.domain_id} contains 'authorized for live'"
            )

    def test_domain_to_dict_roundtrip(self):
        d = _CATALOG[0]
        result = domain_to_dict(d)
        assert result["domain_id"] == d.domain_id
        assert result["target_task_count"] == d.target_task_count

    def test_domains_to_dict_count(self):
        dicts = domains_to_dict(_CATALOG)
        assert len(dicts) == 10

    def test_summarize_domain_catalog(self):
        summary = summarize_domain_catalog(_CATALOG)
        assert summary["domain_count"] == 10
        assert summary["total_target_tasks"] >= 500
        assert summary["frozen_domains"] == 1
        assert summary["human_review_domains"] >= 3
        assert "FROZEN" in summary["risk_level_distribution"]

    def test_frozen_class(self):
        d = _CATALOG[0]
        with pytest.raises(AttributeError):
            d.title = "mutated"  # type: ignore[misc]
