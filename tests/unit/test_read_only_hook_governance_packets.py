"""Tests for read-only hook governance packets (T1041-T1060)."""
from __future__ import annotations

import pytest

from core.read_only_hook_governance_packets import (
    GovernanceSummaryPacket,
    RiskHeatmapPacket,
    DependencyDensityPacket,
    HumanGatePacket,
    ReleaseHoldPacketV2,
    NextPhaseRecommendation,
    ImplementationFreezeList,
    TransitionEntry,
    SafeToImplementChecklist,
    UnsafeToImplementChecklist,
    FinalVerificationPacket,
    T961T1060CloseoutReport,
    build_governance_summary,
    build_risk_heatmap,
    build_dependency_density,
    build_human_gate_pack,
    build_release_hold_v2,
    build_next_phase_recommendation,
    build_implementation_freeze_list,
    build_forbidden_transitions,
    build_approved_transitions,
    build_safe_checklist,
    build_unsafe_checklist,
    build_final_verification,
    build_t961_t1060_closeout,
    governance_summary_to_dict,
    risk_heatmap_to_dict,
    release_hold_v2_to_dict,
    closeout_report_to_dict,
    governance_summary_to_markdown,
    risk_heatmap_to_markdown,
    release_hold_v2_to_markdown,
    closeout_report_to_markdown,
)


class TestGovernancePackets:
    def test_summary_packet(self):
        pkt = build_governance_summary()
        assert isinstance(pkt, GovernanceSummaryPacket)
        assert pkt.task_range == "T961-T1060"
        assert pkt.design_doc_count == 20
        assert pkt.model_module_count == 13
        assert pkt.renderer_module_count == 2
        assert pkt.acceptance_module_count == 1
        assert pkt.test_file_count == 15
        assert pkt.total_tests == 73
        assert pkt.verdict == "PASS"
        assert pkt.release_hold == "HOLD"
        assert len(pkt.notes) > 0

    def test_risk_heatmap(self):
        pkt = build_risk_heatmap()
        assert isinstance(pkt, RiskHeatmapPacket)
        assert pkt.low_count == 0
        assert pkt.medium_count == 0
        assert pkt.high_count == 5
        assert pkt.frozen_count == 0
        assert pkt.total == 5
        assert pkt.recommended_action == "STAGED_EXECUTION"

    def test_dependency_density(self):
        pkt = build_dependency_density()
        assert isinstance(pkt, DependencyDensityPacket)
        assert pkt.module_count == 15
        assert pkt.import_count == 30
        assert pkt.density_level == "medium"

    def test_human_gates(self):
        gates = build_human_gate_pack()
        assert len(gates) == 5
        for gate in gates:
            assert isinstance(gate, HumanGatePacket)
            assert gate.required is True
        gate_ids = [g.gate_id for g in gates]
        assert "HG-001" in gate_ids
        assert "HG-005" in gate_ids

    def test_release_hold_v2(self):
        pkt = build_release_hold_v2()
        assert isinstance(pkt, ReleaseHoldPacketV2)
        assert pkt.hold_active is True
        assert pkt.final_verdict == "HOLD"
        assert pkt.scope == "ALL"
        assert len(pkt.reasons) > 0
        assert len(pkt.release_conditions) > 0

    def test_next_phase_requires_human(self):
        pkt = build_next_phase_recommendation()
        assert isinstance(pkt, NextPhaseRecommendation)
        assert pkt.requires_human_approval is True
        assert pkt.next_phase == "T1061+"
        assert len(pkt.prerequisites) > 0

    def test_freeze_list(self):
        pkt = build_implementation_freeze_list()
        assert isinstance(pkt, ImplementationFreezeList)
        assert "live_runner" in pkt.frozen_components
        assert "order_manager" in pkt.frozen_components
        assert "exchange" in pkt.frozen_components
        assert "planner" in pkt.frozen_components
        assert "secrets" in pkt.frozen_components
        assert len(pkt.frozen_components) == 5

    def test_safe_checklist(self):
        pkt = build_safe_checklist()
        assert isinstance(pkt, SafeToImplementChecklist)
        assert pkt.all_safe is True
        assert len(pkt.items) > 0

    def test_unsafe_checklist(self):
        pkt = build_unsafe_checklist()
        assert isinstance(pkt, UnsafeToImplementChecklist)
        assert len(pkt.items) > 0
        assert "live_runner implementation" in pkt.items
        assert "Live trading authorization" in pkt.items

    def test_final_verification(self):
        pkt = build_final_verification()
        assert isinstance(pkt, FinalVerificationPacket)
        assert pkt.total_tests == 73
        assert pkt.passed == 73
        assert pkt.verdict == "PASS"
        assert len(pkt.test_suites) == 3

    def test_closeout(self):
        pkt = build_t961_t1060_closeout()
        assert isinstance(pkt, T961T1060CloseoutReport)
        assert pkt.task_range == "T961-T1060"
        assert pkt.design_docs_created == 20
        assert pkt.model_modules_created == 13
        assert pkt.renderer_modules_created == 2
        assert pkt.acceptance_modules_created == 1
        assert pkt.governance_modules_created == 1
        assert pkt.test_files_created == 15
        assert pkt.total_tests == 73
        assert pkt.final_verdict == "PASS"
        assert pkt.release_hold == "HOLD"
        assert pkt.hard_stop == "T1060"
        assert "HUMAN_REVIEW_REQUIRED" in pkt.next_safe_phase

    def test_no_live_authorization(self):
        """Verify no packet authorizes live trading."""
        summary = build_governance_summary()
        assert summary.release_hold == "HOLD"
        hold = build_release_hold_v2()
        assert hold.hold_active is True
        assert hold.final_verdict == "HOLD"
        freeze = build_implementation_freeze_list()
        assert "live_runner" in freeze.frozen_components
        assert "exchange" in freeze.frozen_components
        unsafe = build_unsafe_checklist()
        assert "Live trading authorization" in unsafe.items

    def test_deterministic(self):
        """Verify builds produce identical output on repeated calls."""
        pkt1 = build_governance_summary()
        pkt2 = build_governance_summary()
        assert pkt1 == pkt2
        r1 = build_risk_heatmap()
        r2 = build_risk_heatmap()
        assert r1 == r2
        h1 = build_human_gate_pack()
        h2 = build_human_gate_pack()
        assert h1 == h2

    def test_serialization(self):
        """Verify to_dict and to_markdown work."""
        summary = build_governance_summary()
        d = governance_summary_to_dict(summary)
        assert d["task_range"] == "T961-T1060"
        assert d["release_hold"] == "HOLD"
        md = governance_summary_to_markdown(summary)
        assert "T961-T1060" in md
        assert "HOLD" in md

        heatmap = build_risk_heatmap()
        hd = risk_heatmap_to_dict(heatmap)
        assert hd["high_count"] == 5
        hmd = risk_heatmap_to_markdown(heatmap)
        assert "STAGED_EXECUTION" in hmd

        hold = build_release_hold_v2()
        hold_d = release_hold_v2_to_dict(hold)
        assert hold_d["hold_active"] is True
        hold_md = release_hold_v2_to_markdown(hold)
        assert "HOLD" in hold_md

        closeout = build_t961_t1060_closeout()
        cd = closeout_report_to_dict(closeout)
        assert cd["hard_stop"] == "T1060"
        cmd = closeout_report_to_markdown(closeout)
        assert "T1060" in cmd

    def test_forbidden_transitions(self):
        transitions = build_forbidden_transitions()
        assert len(transitions) == 4
        for t in transitions:
            assert isinstance(t, TransitionEntry)
            assert t.allowed is False

    def test_approved_transitions(self):
        transitions = build_approved_transitions()
        assert len(transitions) == 3
        for t in transitions:
            assert isinstance(t, TransitionEntry)
            assert t.allowed is True
