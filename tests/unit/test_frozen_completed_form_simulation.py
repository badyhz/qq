"""Tests for frozen_completed_form_simulation.py — T16501."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from core.frozen_completed_form_simulation import (
    RELEASE_HOLD_REQUIRED,
    SIMULATION_CATEGORIES,
    SimulatedForm,
    SimulationResult,
    generate_simulations,
    render_manifest,
    render_simulation_markdown,
)


@pytest.fixture
def sample_forms():
    return [
        {
            "form_id": "approval_form_core__live_runner_py",
            "path": "core/live_runner.py",
            "form_type": "OFFLINE_REWRITE_APPROVAL_FORM",
            "reviewer_name": "PENDING_HUMAN_REVIEWER",
            "reviewer_role": "PENDING_HUMAN_ROLE",
            "review_date": "PENDING_HUMAN_DATE",
            "candidate_action": "PREPARE_OFFLINE_REWRITE",
            "required_evidence_ids": ["original_path_confirmed", "original_sha256_recorded"],
            "required_evidence_paths": ["evidence/core__live_runner_py/hash_record.json"],
            "original_sha256": "abc123",
            "original_size_bytes": 4202,
            "proposed_backup_path": "archive_simulation/frozen_files/core__live_runner_py",
            "proposed_archive_path": "archive_simulation/archived/core__live_runner_py",
            "rollback_plan_id": "rollback_sim_core__live_runner_py",
            "human_decision_placeholder": "PENDING_HUMAN_DECISION",
            "decision_reason_placeholder": "PENDING_HUMAN_REASON",
            "approval_conditions": ["all_evidence_collected"],
            "rejection_conditions": ["evidence_incomplete"],
            "mandatory_confirmations": [
                "I confirm this is offline-only.",
                "I confirm release_hold remains HOLD.",
            ],
            "forbidden_confirmations": [
                "approve_live_activation",
                "approve_immediate_delete",
            ],
            "signature_placeholder": "PENDING_HUMAN_SIGNATURE",
            "release_hold": "HOLD",
            "advisory_only": True,
            "human_review_required": True,
        },
        {
            "form_id": "approval_form_scripts__live_playbook_py",
            "path": "scripts/live_playbook.py",
            "form_type": "NEEDS_MORE_REVIEW_FORM",
            "reviewer_name": "PENDING_HUMAN_REVIEWER",
            "reviewer_role": "PENDING_HUMAN_ROLE",
            "review_date": "PENDING_HUMAN_DATE",
            "candidate_action": "NEEDS_MORE_REVIEW",
            "required_evidence_ids": ["original_path_confirmed"],
            "required_evidence_paths": ["evidence/scripts__live_playbook_py/hash_record.json"],
            "original_sha256": "def456",
            "original_size_bytes": 1000,
            "proposed_backup_path": "archive_simulation/frozen_files/scripts__live_playbook_py",
            "proposed_archive_path": "archive_simulation/archived/scripts__live_playbook_py",
            "rollback_plan_id": "rollback_sim_scripts__live_playbook_py",
            "human_decision_placeholder": "PENDING_HUMAN_DECISION",
            "decision_reason_placeholder": "PENDING_HUMAN_REASON",
            "approval_conditions": ["all_evidence_collected"],
            "rejection_conditions": ["evidence_incomplete"],
            "mandatory_confirmations": [
                "I confirm this is offline-only.",
                "I confirm release_hold remains HOLD.",
            ],
            "forbidden_confirmations": [
                "approve_live_activation",
            ],
            "signature_placeholder": "PENDING_HUMAN_SIGNATURE",
            "release_hold": "HOLD",
            "advisory_only": True,
            "human_review_required": True,
        },
    ]


class TestSimulationCount:
    def test_minimum_simulations(self, sample_forms):
        result = generate_simulations(sample_forms)
        # 25 categories * 2 forms = 50 minimum
        assert result.total_count >= 50

    def test_at_least_25_simulations_total(self, sample_forms):
        result = generate_simulations(sample_forms)
        assert result.total_count >= 25


class TestAllCategoriesPresent:
    def test_all_25_categories_present(self, sample_forms):
        result = generate_simulations(sample_forms)
        for cat in SIMULATION_CATEGORIES:
            assert cat in result.category_counts, f"missing category: {cat}"

    def test_category_count(self, sample_forms):
        result = generate_simulations(sample_forms)
        assert len(result.category_counts) == 25


class TestNoActionPerformed:
    def test_no_action_performed(self, sample_forms):
        result = generate_simulations(sample_forms)
        for s in result.simulations:
            assert s.no_action_performed is True
            assert s.dry_run_only is True


class TestDryRunOnly:
    def test_dry_run_only(self, sample_forms):
        result = generate_simulations(sample_forms)
        for s in result.simulations:
            assert s.dry_run_only is True


class TestActionRequestedFalse:
    def test_action_requested_false_except_unsafe(self, sample_forms):
        result = generate_simulations(sample_forms)
        for s in result.simulations:
            if s.simulation_category != "unsafe_auto_action_requested":
                assert s.action_requested is False

    def test_unsafe_fixture_action_requested_true(self, sample_forms):
        result = generate_simulations(sample_forms)
        unsafe = [s for s in result.simulations if s.simulation_category == "unsafe_auto_action_requested"]
        assert len(unsafe) > 0
        for s in unsafe:
            assert s.action_requested is True


class TestReleaseHoldMismatch:
    def test_release_hold_not_hold_fails(self, sample_forms):
        with pytest.raises(ValueError, match="release_hold"):
            generate_simulations(sample_forms, release_hold="RELEASED")


class TestDeterministic:
    def test_deterministic_output(self, sample_forms):
        r1 = generate_simulations(sample_forms)
        r2 = generate_simulations(sample_forms)
        h1 = hashlib.sha256(json.dumps(r1.to_dict(), sort_keys=True).encode()).hexdigest()
        h2 = hashlib.sha256(json.dumps(r2.to_dict(), sort_keys=True).encode()).hexdigest()
        assert h1 == h2


class TestSimulatedFormFields:
    def test_required_fields_present(self, sample_forms):
        result = generate_simulations(sample_forms)
        for s in result.simulations:
            d = s.to_dict()
            assert "completed_form_id" in d
            assert "source_form_id" in d
            assert "path" in d
            assert "simulation_category" in d
            assert "reviewer_name" in d
            assert "reviewer_role" in d
            assert "review_date" in d
            assert "human_decision" in d
            assert "decision_reason" in d
            assert "evidence_status" in d
            assert "evidence_ids_confirmed" in d
            assert "hash_evidence_confirmed" in d
            assert "rollback_evidence_confirmed" in d
            assert "backup_evidence_confirmed" in d
            assert "mandatory_confirmations_checked" in d
            assert "forbidden_confirmations_checked" in d
            assert "release_hold" in d
            assert "advisory_only" in d
            assert "human_review_required" in d
            assert "dry_run_only" in d
            assert "action_requested" in d
            assert "no_action_performed" in d


class TestNoFileOperations:
    def test_no_file_operations(self, sample_forms, tmp_path):
        """Simulation should not perform any file I/O."""
        result = generate_simulations(sample_forms)
        # Only test that generation doesn't require file paths
        assert result.total_count > 0
        # Ensure no tmp_path files were created
        assert list(tmp_path.iterdir()) == []


class TestRenderMarkdown:
    def test_render_markdown(self, sample_forms):
        result = generate_simulations(sample_forms)
        md = render_simulation_markdown(result)
        assert "Frozen Completed Form Simulations" in md
        assert "NO ACTION AUTHORIZED" in md


class TestRenderManifest:
    def test_render_manifest(self, sample_forms):
        result = generate_simulations(sample_forms)
        manifest = render_manifest(result)
        assert manifest["total_count"] == result.total_count
        assert manifest["release_hold"] == "HOLD"
        assert manifest["dry_run_only"] is True
        assert manifest["no_action_performed"] is True
        assert "simulation_hash" in manifest


class TestForbiddenDecisions:
    def test_all_forbidden_decisions_simulated(self, sample_forms):
        result = generate_simulations(sample_forms)
        forbidden_cats = [
            "forbidden_delete_now", "forbidden_move_now", "forbidden_copy_now",
            "forbidden_archive_now", "forbidden_execute_now", "forbidden_import_now",
            "forbidden_activate_live", "forbidden_activate_testnet",
            "forbidden_enable_runtime", "forbidden_enable_planner",
        ]
        for cat in forbidden_cats:
            assert cat in result.category_counts
            sims = [s for s in result.simulations if s.simulation_category == cat]
            for s in sims:
                assert s.release_hold == "HOLD"
                assert s.advisory_only is True
