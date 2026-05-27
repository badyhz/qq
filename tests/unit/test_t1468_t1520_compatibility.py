"""Compatibility tests for T1468-T1520 review-to-decision operating system."""

import os
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEV_PRD_DIR = os.path.join(REPO_ROOT, "docs", "dev_prd")


def _read_file(rel_path):
    abs_path = os.path.join(REPO_ROOT, rel_path)
    with open(abs_path, "r") as f:
        return f.read()


class TestTaskQueueContainsT1441:
    """Verify runtime_governance_task_queue.md references T1441-T1520."""

    def test_task_queue_references_t1441(self):
        content = _read_file("docs/dev_prd/runtime_governance_task_queue.md")
        assert "T1441" in content, "task_queue must reference T1441"

    def test_task_queue_references_t1520(self):
        content = _read_file("docs/dev_prd/runtime_governance_task_queue.md")
        assert "T1520" in content, "task_queue must reference T1520"

    def test_task_queue_has_review_to_decision_completed_range(self):
        content = _read_file("docs/dev_prd/runtime_governance_task_queue.md")
        assert "review-to-decision operating system" in content


class TestCurrentStateUpdated:
    """Verify runtime_governance_current_state.md has review-to-decision section."""

    def test_current_state_has_review_to_decision_section(self):
        content = _read_file("docs/dev_prd/runtime_governance_current_state.md")
        assert "Review-to-Decision Operating System" in content

    def test_current_state_references_t1520(self):
        content = _read_file("docs/dev_prd/runtime_governance_current_state.md")
        assert "T1520" in content


class TestCloseoutDocsExist:
    """Verify all closeout documentation files exist."""

    EXPECTED_FILES = [
        "review_to_decision_overview.md",
        "frozen_file_review_packet_spec.md",
        "promotion_readiness_scoring_spec.md",
        "human_approval_transcript_spec.md",
        "unlock_recommendation_spec.md",
        "hold_decision_report_spec.md",
        "review_to_decision_closeout.md",
        "t1441_t1520_governance_summary_packet.md",
        "t1441_t1520_final_closeout_report.md",
    ]

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_closeout_doc_exists(self, filename):
        path = os.path.join(DEV_PRD_DIR, filename)
        assert os.path.isfile(path), f"Missing: {filename}"


class TestCompatibilityIntegration:
    """Cross-cutting compatibility checks."""

    def test_all_specs_mention_release_hold(self):
        specs = [
            "frozen_file_review_packet_spec.md",
            "promotion_readiness_scoring_spec.md",
            "human_approval_transcript_spec.md",
            "unlock_recommendation_spec.md",
            "hold_decision_report_spec.md",
        ]
        for spec in specs:
            content = _read_file(f"docs/dev_prd/{spec}")
            assert "Release hold" in content or "release_hold" in content or "HOLD" in content, \
                f"{spec} must reference release hold"

    def test_overview_references_all_specs(self):
        content = _read_file("docs/dev_prd/review_to_decision_overview.md")
        for spec_name in [
            "frozen_file_review_packet_spec",
            "promotion_readiness_scoring_spec",
            "human_approval_transcript_spec",
            "unlock_recommendation_spec",
            "hold_decision_report_spec",
        ]:
            assert spec_name in content, f"overview must reference {spec_name}"
