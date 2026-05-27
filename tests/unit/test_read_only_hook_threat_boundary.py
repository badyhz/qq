"""Tests for read-only hook threat model and boundary map — pure pytest, no I/O."""
from core.read_only_hook_threat_model import (
    THREAT_IDS,
    ThreatModelItem,
    build_default_threat_model,
    threat_model_item_to_dict,
)
from core.read_only_hook_boundary_map import (
    BoundaryEntry,
    build_boundary_map,
    boundary_entry_to_dict,
)


class TestThreatModel:
    def test_default_threats(self):
        threats = build_default_threat_model()
        assert len(threats) == 5
        assert all(isinstance(t, ThreatModelItem) for t in threats)
        assert len(THREAT_IDS) == 5
        for t in threats:
            assert t.threat_id in THREAT_IDS
            assert t.status in ("mitigated", "accepted", "open")

    def test_to_dict(self):
        threats = build_default_threat_model()
        d = threat_model_item_to_dict(threats[0])
        assert "threat_id" in d
        assert "title" in d
        assert "severity" in d
        assert "mitigation" in d
        assert "status" in d


class TestBoundaryMap:
    def test_default_boundaries(self):
        boundaries = build_boundary_map()
        assert len(boundaries) == 10
        assert all(isinstance(b, BoundaryEntry) for b in boundaries)

    def test_forbidden_entries(self):
        boundaries = build_boundary_map()
        forbidden = {b.component: b for b in boundaries if b.access_level == "forbidden"}
        # network, filesystem, exchange, planner — check semantic equivalents
        assert "data_feed" in forbidden
        assert "execution" in forbidden
        assert "order_manager" in forbidden
        assert "signal_engine" in forbidden
