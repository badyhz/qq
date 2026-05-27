"""Tests for runtime governance preflight packet.

Sync only. No async. No I/O. No network. No random.
"""

from __future__ import annotations

import pytest

from core.runtime_governance_contract import RuntimeGovernanceInput
from core.runtime_governance_preflight_packet import (
    RuntimeGovernancePreflightPacket,
    build_runtime_governance_preflight_packet,
    preflight_packet_to_dict,
    preflight_packet_to_markdown,
)


# ── fixtures ──────────────────────────────────────────────────────────


def _valid_input(**overrides) -> RuntimeGovernanceInput:
    defaults = dict(
        run_id="run-001",
        adapter_id="adapter-001",
        mode="dry_run",
        requested_action="scan",
        symbol="BTCUSDT",
        environment="test",
        allow_network=False,
        allow_submit=False,
        allow_file_io=False,
        metadata={},
    )
    defaults.update(overrides)
    return RuntimeGovernanceInput(**defaults)


# ── tests ─────────────────────────────────────────────────────────────


class TestValidInputPass:
    def test_valid_input_passes(self):
        pkt = build_runtime_governance_preflight_packet(_valid_input())

        assert pkt.final_verdict == "PASS"
        assert pkt.proceed is True
        assert pkt.dry_run_result.contract_result.ok is True
        assert pkt.dry_run_result.contract_result.failures == []


class TestInvalidInputMissingRunId:
    def test_missing_run_id_fails(self):
        pkt = build_runtime_governance_preflight_packet(_valid_input(run_id=""))

        assert pkt.final_verdict == "FAIL"
        assert pkt.proceed is False
        assert len(pkt.dry_run_result.contract_result.failures) > 0


class TestPolicyBlock:
    def test_allow_submit_in_prod_blocked(self):
        pkt = build_runtime_governance_preflight_packet(
            _valid_input(allow_submit=True, environment="prod")
        )

        assert pkt.final_verdict == "BLOCKED"
        assert pkt.proceed is False


class TestSnapshotMismatch:
    def test_snapshot_mismatch_fails(self):
        expected = "# Runtime Governance Dry-Run Report\n\n**Verdict:** FAIL\n"
        pkt = build_runtime_governance_preflight_packet(
            _valid_input(), expected_markdown=expected
        )

        assert pkt.dry_run_result.packet.snapshot_diff.ok is False
        assert pkt.final_verdict == "FAIL"
        assert pkt.proceed is False


class TestDictSerializationKeys:
    def test_dict_has_all_expected_keys(self):
        pkt = build_runtime_governance_preflight_packet(_valid_input())
        d = preflight_packet_to_dict(pkt)

        expected_keys = {
            "input",
            "dry_run_result",
            "audit_event",
            "final_verdict",
            "proceed",
            "notes",
        }
        assert expected_keys == set(d.keys())

        # nested keys
        assert "run_id" in d["input"]
        assert "contract_result" in d["dry_run_result"]
        assert "event_id" in d["audit_event"]


class TestMarkdownContainsVerdict:
    def test_markdown_contains_verdict_and_proceed(self):
        pkt = build_runtime_governance_preflight_packet(_valid_input())
        md = preflight_packet_to_markdown(pkt)

        assert "**Final Verdict:** PASS" in md
        assert "**Proceed:** True" in md


class TestMarkdownDeterministic:
    def test_markdown_same_on_repeat(self):
        pkt = build_runtime_governance_preflight_packet(_valid_input())
        md1 = preflight_packet_to_markdown(pkt)
        md2 = preflight_packet_to_markdown(pkt)

        assert md1 == md2


class TestMarkdownNoTimestamps:
    def test_no_timestamps(self):
        pkt = build_runtime_governance_preflight_packet(_valid_input())
        md = preflight_packet_to_markdown(pkt)

        for marker in ["timestamp", "created_at", "updated_at", "date:", "time:"]:
            assert marker not in md.lower()


class TestAuditEventRunId:
    def test_audit_event_has_correct_run_id(self):
        pkt = build_runtime_governance_preflight_packet(_valid_input(run_id="run-abc"))

        assert pkt.audit_event.run_id == "run-abc"
        assert pkt.audit_event.adapter_id == "adapter-001"
        assert pkt.audit_event.action == "scan"
        assert pkt.audit_event.verdict == "PASS"


class TestNotesPassthrough:
    def test_notes_collected(self):
        pkt = build_runtime_governance_preflight_packet(
            _valid_input(), notes=["note-a", "note-b"]
        )

        assert "note-a" in pkt.notes
        assert "note-b" in pkt.notes
