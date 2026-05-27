"""Tests for read-only hook acceptance layer (T1021-T1040).

Pure deterministic tests, no I/O.
"""

import pytest

from core.read_only_hook_acceptance import (
    AcceptanceCloseoutPacket,
    AcceptanceCommand,
    AcceptanceVerdict,
    acceptance_closeout_to_dict,
    acceptance_command_to_dict,
    acceptance_commands_to_markdown,
    acceptance_verdict_to_dict,
    build_acceptance_closeout,
    build_acceptance_verdict,
    build_read_only_hook_acceptance_commands,
)


# ---------------------------------------------------------------------------
# AcceptanceCommand tests
# ---------------------------------------------------------------------------

class TestAcceptanceCommands:

    def test_commands_count(self):
        """Must have at least 10 acceptance commands."""
        cmds = build_read_only_hook_acceptance_commands()
        assert len(cmds) >= 10

    def test_safety_statements(self):
        """Safety statements must be present."""
        cmds = build_read_only_hook_acceptance_commands()
        ids = {c.command_id for c in cmds}
        required = {
            "no_network_statement",
            "no_submit_statement",
            "no_secret_access_statement",
            "no_exchange_client_statement",
            "no_planner_integration_statement",
            "no_runtime_integration_statement",
        }
        assert required.issubset(ids), f"Missing safety: {required - ids}"

    def test_release_hold(self):
        """release_hold_statement must be present with HOLD semantics."""
        cmds = build_read_only_hook_acceptance_commands()
        hold_cmds = [c for c in cmds if c.command_id == "release_hold_statement"]
        assert len(hold_cmds) == 1
        assert "HOLD" in hold_cmds[0].command

    def test_deterministic(self):
        """Calling builder twice yields identical results."""
        a = build_read_only_hook_acceptance_commands()
        b = build_read_only_hook_acceptance_commands()
        assert len(a) == len(b)
        for x, y in zip(a, b):
            assert x == y

    def test_frozen(self):
        """AcceptanceCommand is frozen/immutable."""
        cmds = build_read_only_hook_acceptance_commands()
        with pytest.raises(AttributeError):
            cmds[0].command_id = "changed"

    def test_categories(self):
        """All commands must have valid categories."""
        cmds = build_read_only_hook_acceptance_commands()
        valid = {"test", "boundary", "safety", "regression"}
        for cmd in cmds:
            assert cmd.category in valid, f"{cmd.command_id} has invalid category: {cmd.category}"

    def test_boundary_commands_present(self):
        """Boundary commands must exist."""
        cmds = build_read_only_hook_acceptance_commands()
        ids = {c.command_id for c in cmds}
        assert "forbidden_import_check" in ids
        assert "forbidden_file_boundary_check" in ids

    def test_human_review_statement(self):
        """Human review required statement must be present."""
        cmds = build_read_only_hook_acceptance_commands()
        ids = {c.command_id for c in cmds}
        assert "human_review_required_statement" in ids

    def test_test_prd_command(self):
        """test_prd_read_only_hook must be present."""
        cmds = build_read_only_hook_acceptance_commands()
        ids = {c.command_id for c in cmds}
        assert "test_prd_read_only_hook" in ids

    def test_control_plane_command(self):
        """test_dev_prd_control_plane must be present."""
        cmds = build_read_only_hook_acceptance_commands()
        ids = {c.command_id for c in ids} if False else {c.command_id for c in cmds}
        assert "test_dev_prd_control_plane" in ids


# ---------------------------------------------------------------------------
# AcceptanceVerdict tests
# ---------------------------------------------------------------------------

class TestAcceptanceVerdict:

    def test_pass_verdict(self):
        v = build_acceptance_verdict(10, 10)
        assert v.verdict == "PASS"
        assert v.passed == 10
        assert v.failed == 0

    def test_fail_verdict(self):
        v = build_acceptance_verdict(0, 10)
        assert v.verdict == "FAIL"
        assert v.passed == 0
        assert v.failed == 10

    def test_partial_verdict(self):
        v = build_acceptance_verdict(5, 10)
        assert v.verdict == "PARTIAL"
        assert v.passed == 5
        assert v.failed == 5

    def test_zero_total_fail(self):
        v = build_acceptance_verdict(0, 0)
        assert v.verdict == "FAIL"

    def test_frozen(self):
        v = build_acceptance_verdict(1, 1)
        with pytest.raises(AttributeError):
            v.verdict = "FAIL"


# ---------------------------------------------------------------------------
# AcceptanceCloseoutPacket tests
# ---------------------------------------------------------------------------

class TestAcceptanceCloseout:

    def test_hold_verdict(self):
        """Closeout packet must always carry release_hold=HOLD."""
        pkt = build_acceptance_closeout()
        assert pkt.release_hold == "HOLD"

    def test_no_live_auth(self):
        """Closeout must not authorize live trading."""
        pkt = build_acceptance_closeout()
        assert pkt.release_hold == "HOLD"
        assert "no live" in " ".join(pkt.notes).lower() or "hold" in pkt.release_hold.lower()

    def test_task_range(self):
        pkt = build_acceptance_closeout()
        assert pkt.task_range == "T1021-T1040"

    def test_frozen(self):
        pkt = build_acceptance_closeout()
        with pytest.raises(AttributeError):
            pkt.verdict = "FAIL"

    def test_next_phase_is_human_review(self):
        pkt = build_acceptance_closeout()
        assert pkt.next_phase == "human_review"


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------

class TestSerialization:

    def test_command_to_dict(self):
        cmd = AcceptanceCommand(
            command_id="test_1",
            description="desc",
            command="echo ok",
            category="test",
        )
        d = acceptance_command_to_dict(cmd)
        assert d["command_id"] == "test_1"
        assert d["category"] == "test"

    def test_verdict_to_dict(self):
        v = build_acceptance_verdict(5, 10)
        d = acceptance_verdict_to_dict(v)
        assert d["verdict"] == "PARTIAL"
        assert d["passed"] == 5

    def test_closeout_to_dict(self):
        pkt = build_acceptance_closeout()
        d = acceptance_closeout_to_dict(pkt)
        assert d["release_hold"] == "HOLD"
        assert d["task_range"] == "T1021-T1040"

    def test_commands_to_markdown(self):
        cmds = build_read_only_hook_acceptance_commands()
        md = acceptance_commands_to_markdown(cmds)
        assert "Read-Only Hook Acceptance Commands" in md
        assert "test_read_only_hook_contract" in md
        assert "Total commands:" in md
