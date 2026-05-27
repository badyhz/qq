"""Tests for read-only hook evidence — pure pytest, no I/O."""
from core.read_only_hook_evidence import (
    EvidenceRecord,
    build_evidence_record,
    evidence_to_dict,
)


class TestEvidence:
    def test_build_evidence(self):
        ev = build_evidence_record(
            evidence_id="ev_01",
            hook_id="h1",
            operation="query",
            result_status="success",
            invariants_checked=["no_mutation", "no_network"],
            invariants_passed=["no_mutation", "no_network"],
            notes=["all clear"],
        )
        assert isinstance(ev, EvidenceRecord)
        assert ev.evidence_id == "ev_01"
        assert ev.hook_id == "h1"
        assert len(ev.invariants_checked) == 2

    def test_to_dict(self):
        ev = build_evidence_record(
            "ev_02", "h2", "inspect", "denied", ["no_secrets"], [], ["blocked"]
        )
        d = evidence_to_dict(ev)
        assert d == {
            "evidence_id": "ev_02",
            "hook_id": "h2",
            "operation": "inspect",
            "result_status": "denied",
            "invariants_checked": ["no_secrets"],
            "invariants_passed": [],
            "notes": ["blocked"],
        }
        d["evidence_id"] = "changed"
        assert ev.evidence_id == "ev_02"

    def test_deterministic(self):
        ev = build_evidence_record("ev_03", "h3", "query", "success", ["a"], ["a"], [])
        d1 = evidence_to_dict(ev)
        d2 = evidence_to_dict(ev)
        assert d1 == d2
