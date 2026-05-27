"""T1447 - Tests for FrozenFileReviewPacket, FrozenReviewCheck, generator, renderer."""
from __future__ import annotations

import pytest


class TestFrozenReviewCheck:
    """Tests for FrozenReviewCheck (T1442)."""

    def test_create_check_frozen(self):
        from core.frozen_review_check import build_review_check

        check = build_review_check(
            check_id="RC-001",
            check_name="No live imports",
            check_type="IMPORT_BOUNDARY",
            description="Verify no live imports",
        )
        assert check.check_id == "RC-001"
        assert check.check_type.value == "IMPORT_BOUNDARY"
        assert check.status.value == "PENDING"

    def test_check_immutability(self):
        from core.frozen_review_check import build_review_check

        check = build_review_check(check_id="RC-002", check_name="test", check_type="NETWORK_FREE")
        with pytest.raises(AttributeError):
            check.status = "PASS"  # type: ignore[misc]

    def test_check_invalid_type(self):
        from core.frozen_review_check import build_review_check

        with pytest.raises(ValueError):
            build_review_check(check_id="RC-003", check_name="bad", check_type="INVALID")


class TestFrozenFileReviewPacket:
    """Tests for FrozenFileReviewPacket (T1441)."""

    def test_create_packet_frozen(self):
        from core.frozen_file_review_packet import build_review_packet

        pkt = build_review_packet(
            packet_id="PKT-001",
            file_path="scripts/run_foo.py",
            risk_class="HIGH",
            file_category="script",
        )
        assert pkt.packet_id == "PKT-001"
        assert pkt.risk_class.value == "HIGH"
        assert pkt.decision_status.value == "PENDING"

    def test_packet_immutability(self):
        from core.frozen_file_review_packet import build_review_packet

        pkt = build_review_packet(packet_id="PKT-002", file_path="core/x.py", risk_class="MEDIUM")
        with pytest.raises(AttributeError):
            pkt.decision_status = "APPROVED"  # type: ignore[misc]


class TestReviewPacketGenerator:
    """Tests for generate_review_packet (T1445)."""

    def test_high_has_more_checks_than_medium(self):
        from core.frozen_review_packet_generator import generate_review_packet

        high = generate_review_packet("scripts/live_playbook.py", "HIGH")
        medium = generate_review_packet("scripts/run_foo.py", "MEDIUM")
        assert len(high.review_checks) > len(medium.review_checks)

    def test_high_gets_6_checks(self):
        from core.frozen_review_packet_generator import generate_review_packet

        pkt = generate_review_packet("core/live_runner.py", "HIGH")
        assert len(pkt.review_checks) == 6

    def test_medium_gets_4_checks(self):
        from core.frozen_review_packet_generator import generate_review_packet

        pkt = generate_review_packet("scripts/run_foo.py", "MEDIUM")
        assert len(pkt.review_checks) == 4

    def test_high_evidence_count(self):
        from core.frozen_review_packet_generator import generate_review_packet

        pkt = generate_review_packet("scripts/live_playbook.py", "HIGH")
        assert len(pkt.evidence_requirements) == 5

    def test_medium_evidence_count(self):
        from core.frozen_review_packet_generator import generate_review_packet

        pkt = generate_review_packet("scripts/run_foo.py", "MEDIUM")
        assert len(pkt.evidence_requirements) == 2

    def test_deterministic_output(self):
        from core.frozen_review_packet_generator import generate_review_packet

        a = generate_review_packet("core/x.py", "HIGH")
        b = generate_review_packet("core/x.py", "HIGH")
        assert a.packet_id == b.packet_id
        assert len(a.review_checks) == len(b.review_checks)

    def test_scripts_category(self):
        from core.frozen_review_packet_generator import generate_review_packet

        pkt = generate_review_packet("scripts/foo.py", "MEDIUM")
        assert pkt.file_category == "script"

    def test_core_category(self):
        from core.frozen_review_packet_generator import generate_review_packet

        pkt = generate_review_packet("core/bar.py", "HIGH")
        assert pkt.file_category == "core"


class TestReviewPacketRenderer:
    """Tests for render functions (T1446)."""

    def test_render_packet_md(self):
        from core.frozen_review_packet_generator import generate_review_packet
        from core.frozen_review_packet_renderer import render_review_packet_md

        pkt = generate_review_packet("scripts/live_playbook.py", "HIGH")
        md = render_review_packet_md(pkt)
        assert "Frozen File Review Packet" in md
        assert "scripts/live_playbook.py" in md
        assert "HIGH" in md

    def test_render_checklist_md(self):
        from core.frozen_file_risk_requirement import build_risk_requirement
        from core.frozen_risk_requirement_checklist import build_checklist
        from core.frozen_review_packet_renderer import render_checklist_md

        req = build_risk_requirement(requirement_id="RR-001", risk_class="HIGH", requirement_name="test")
        cl = build_checklist(checklist_id="CL-001", file_path="core/x.py", risk_class="HIGH", requirements=(req,))
        md = render_checklist_md(cl)
        assert "Frozen Risk Requirement Checklist" in md
