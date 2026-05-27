"""Tests for Governance Registry — T1369.

Frozen dataclass creation, immutability, domain entries, layer index,
cross-references, build_verdict validation. Pure tests, no I/O.
"""
from __future__ import annotations

import pytest

from core.governance_registry import GovernanceRegistry
from core.governance_domain_entry import GovernanceDomainEntry
from core.governance_layer_index import GovernanceLayerIndex
from core.governance_layer_entry import GovernanceLayerEntry
from core.governance_domain_status import GovernanceDomainStatus, ALL_STATUSES
from core.governance_cross_reference import GovernanceCrossReference
from core.governance_registry_verdict import GovernanceRegistryVerdict, build_verdict
from core.governance_registry_renderer import (
    render_governance_registry_md,
    render_governance_domain_entry_md,
    render_governance_layer_index_md,
    render_governance_registry_verdict_md,
)


# ── helpers ──────────────────────────────────────────────────────────


def _make_domain(domain_id: str = "D1", status: str = "COMPLETE") -> GovernanceDomainEntry:
    return GovernanceDomainEntry(
        domain_id=domain_id,
        domain_name=f"Domain {domain_id}",
        task_range="T961-T1060",
        layer_name="Read-Only Hook Design",
        doc_count=20,
        model_count=13,
        test_count=15,
        status=status,
    )


def _make_layer(layer_id: str = "L1", domain_ids: tuple = ("D1",)) -> GovernanceLayerEntry:
    return GovernanceLayerEntry(
        layer_id=layer_id,
        name="Read-Only Hook Design",
        task_range="T961-T1060",
        description="Read-only hook contracts and models",
        domains=domain_ids,
        hard_stop="T1060",
    )


def _make_registry(domains: tuple | None = None) -> GovernanceRegistry:
    if domains is None:
        domains = (_make_domain("D1"), _make_domain("D2"))
    return GovernanceRegistry(
        registry_id="REG-001",
        domains=domains,
        version="1.0.0",
        created_by="agent",
    )


def _make_layer_index(layers: tuple | None = None, total_domains: int = 2) -> GovernanceLayerIndex:
    if layers is None:
        layers = (_make_layer("L1", ("D1", "D2")),)
    return GovernanceLayerIndex(
        index_id="IDX-001",
        layers=layers,
        total_domains=total_domains,
        total_models=33,
        total_docs=40,
        total_tests=20,
    )


# ── T1361: GovernanceRegistry frozen ────────────────────────────────


def test_registry_frozen() -> None:
    reg = _make_registry()
    assert reg.registry_id == "REG-001"
    assert len(reg.domains) == 2
    assert reg.version == "1.0.0"


def test_registry_immutability() -> None:
    reg = _make_registry()
    with pytest.raises(AttributeError):
        reg.registry_id = "CHANGED"  # type: ignore[misc]


# ── T1362: GovernanceDomainEntry ────────────────────────────────────


def test_domain_entry_fields() -> None:
    d = _make_domain("D3")
    assert d.domain_id == "D3"
    assert d.task_range == "T961-T1060"
    assert d.layer_name == "Read-Only Hook Design"
    assert d.doc_count == 20
    assert d.model_count == 13
    assert d.test_count == 15


def test_domain_entry_frozen() -> None:
    d = _make_domain()
    with pytest.raises(AttributeError):
        d.status = "BLOCKED"  # type: ignore[misc]


# ── T1363: GovernanceLayerIndex ─────────────────────────────────────


def test_layer_index_fields() -> None:
    idx = _make_layer_index()
    assert idx.index_id == "IDX-001"
    assert idx.total_domains == 2
    assert idx.total_models == 33
    assert idx.total_docs == 40
    assert idx.total_tests == 20


def test_layer_index_frozen() -> None:
    idx = _make_layer_index()
    with pytest.raises(AttributeError):
        idx.total_domains = 999  # type: ignore[misc]


# ── T1364: GovernanceLayerEntry ─────────────────────────────────────


def test_layer_entry_fields() -> None:
    layer = _make_layer("L2", ("D5", "D6"))
    assert layer.layer_id == "L2"
    assert layer.name == "Read-Only Hook Design"
    assert layer.domains == ("D5", "D6")
    assert layer.hard_stop == "T1060"


# ── T1365: GovernanceDomainStatus ───────────────────────────────────


def test_domain_status_valid() -> None:
    for status in ALL_STATUSES:
        ds = GovernanceDomainStatus(
            domain_id="D1", status=status, completion_pct=50.0, blockers=()
        )
        assert ds.status == status


def test_domain_status_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid status"):
        GovernanceDomainStatus(
            domain_id="D1", status="INVALID", completion_pct=0.0, blockers=()
        )


def test_domain_status_blockers_tuple() -> None:
    ds = GovernanceDomainStatus(
        domain_id="D1", status="BLOCKED", completion_pct=25.0,
        blockers=("missing tests", "missing docs")
    )
    assert len(ds.blockers) == 2
    assert "missing tests" in ds.blockers


# ── T1366: GovernanceCrossReference ─────────────────────────────────


def test_cross_reference_fields() -> None:
    ref = GovernanceCrossReference(
        ref_id="XREF-001",
        source_domain="D1",
        target_domain="D2",
        relationship="depends_on",
        description="D1 depends on D2 for freeze policy",
    )
    assert ref.ref_id == "XREF-001"
    assert ref.relationship == "depends_on"


def test_cross_reference_frozen() -> None:
    ref = GovernanceCrossReference(
        ref_id="XREF-001", source_domain="D1", target_domain="D2",
        relationship="depends_on", description="test"
    )
    with pytest.raises(AttributeError):
        ref.source_domain = "CHANGED"  # type: ignore[misc]


# ── T1367: build_verdict ────────────────────────────────────────────


def test_build_verdict_pass() -> None:
    reg = _make_registry((_make_domain("D1"), _make_domain("D2")))
    idx = _make_layer_index(
        (_make_layer("L1", ("D1", "D2")),), total_domains=2
    )
    v = build_verdict(reg, idx)
    assert v.verdict == "PASS"
    assert len(v.missing_domains) == 0
    assert len(v.inconsistencies) == 0


def test_build_verdict_fail_missing_domain() -> None:
    reg = _make_registry((_make_domain("D1"),))  # only D1
    idx = _make_layer_index(
        (_make_layer("L1", ("D1", "D2")),), total_domains=2
    )
    v = build_verdict(reg, idx)
    assert v.verdict == "FAIL"
    assert "D2" in v.missing_domains


def test_build_verdict_fail_count_mismatch() -> None:
    reg = _make_registry((_make_domain("D1"), _make_domain("D2")))
    idx = _make_layer_index(
        (_make_layer("L1", ("D1", "D2")),), total_domains=5  # mismatch
    )
    v = build_verdict(reg, idx)
    assert v.verdict == "FAIL"
    assert any("count mismatch" in i for i in v.inconsistencies)


def test_build_verdict_fail_duplicate_domain() -> None:
    reg = _make_registry((_make_domain("D1"), _make_domain("D1")))
    idx = _make_layer_index(
        (_make_layer("L1", ("D1",)),), total_domains=2
    )
    v = build_verdict(reg, idx)
    assert v.verdict == "FAIL"
    assert any("Duplicate" in i for i in v.inconsistencies)


# ── T1368: renderers ────────────────────────────────────────────────


def test_render_registry_md() -> None:
    reg = _make_registry()
    md = render_governance_registry_md(reg)
    assert "REG-001" in md
    assert "1.0.0" in md
    assert "Domain D1" in md


def test_render_domain_entry_md() -> None:
    d = _make_domain("D5")
    md = render_governance_domain_entry_md(d)
    assert "D5" in md
    assert "T961-T1060" in md


def test_render_layer_index_md() -> None:
    idx = _make_layer_index()
    md = render_governance_layer_index_md(idx)
    assert "IDX-001" in md
    assert "Total Domains" in md


def test_render_verdict_md() -> None:
    v = GovernanceRegistryVerdict(
        verdict="PASS", notes="ok", missing_domains=(), inconsistencies=()
    )
    md = render_governance_registry_verdict_md(v)
    assert "PASS" in md
    assert "ok" in md


def test_render_verdict_md_with_failures() -> None:
    v = GovernanceRegistryVerdict(
        verdict="FAIL", notes="issues found",
        missing_domains=("D3",), inconsistencies=("Duplicate domain_id: D1",)
    )
    md = render_governance_registry_verdict_md(v)
    assert "FAIL" in md
    assert "D3" in md
    assert "Duplicate" in md
