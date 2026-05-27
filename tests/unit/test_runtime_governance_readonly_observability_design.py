"""T846: Tests for runtime governance read-only observability design."""

import pytest
from core.runtime_governance_readonly_observability_design import (
    RuntimeGovernanceReadOnlyObservationPoint,
    build_readonly_observability_design,
    readonly_observability_design_to_dict,
    readonly_observability_design_to_markdown,
)


class TestObservationPointCount:
    def test_exactly_seven_points(self):
        points = build_readonly_observability_design()
        assert len(points) == 7


class TestCriticalSensitivityRules:
    def test_critical_requires_encrypted_storage(self):
        points = build_readonly_observability_design()
        for p in points:
            if p.sensitivity == "critical":
                assert p.allowed_storage == "encrypted"

    def test_critical_requires_full_redaction(self):
        points = build_readonly_observability_design()
        for p in points:
            if p.sensitivity == "critical":
                assert p.redaction == "full"


class TestNoRawSecrets:
    def test_no_raw_secrets_in_design(self):
        points = build_readonly_observability_design()
        for p in points:
            for field_val in [p.point_id, p.signal, p.sensitivity, p.allowed_storage, p.redaction]:
                assert "secret" not in field_val.lower()
                assert "password" not in field_val.lower()
                assert "key" not in field_val.lower() or p.point_id == "blocker_summary"


class TestDeterminism:
    def test_deterministic_build(self):
        a = build_readonly_observability_design()
        b = build_readonly_observability_design()
        assert a == b

    def test_deterministic_to_dict(self):
        pts = build_readonly_observability_design()
        assert readonly_observability_design_to_dict(pts) == readonly_observability_design_to_dict(pts)

    def test_deterministic_to_markdown(self):
        pts = build_readonly_observability_design()
        assert readonly_observability_design_to_markdown(pts) == readonly_observability_design_to_markdown(pts)


class TestToDict:
    def test_returns_list_of_dicts(self):
        pts = build_readonly_observability_design()
        result = readonly_observability_design_to_dict(pts)
        assert isinstance(result, list)
        assert len(result) == 7
        for d in result:
            assert isinstance(d, dict)
            assert "point_id" in d
            assert "signal" in d
            assert "sensitivity" in d
            assert "allowed_storage" in d
            assert "redaction" in d
            assert "notes" in d


class TestMarkdown:
    def test_contains_all_point_ids(self):
        pts = build_readonly_observability_design()
        md = readonly_observability_design_to_markdown(pts)
        for p in pts:
            assert p.point_id in md

    def test_contains_table_header(self):
        pts = build_readonly_observability_design()
        md = readonly_observability_design_to_markdown(pts)
        assert "point_id" in md
        assert "signal" in md
        assert "sensitivity" in md
