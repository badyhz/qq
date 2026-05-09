"""Targeted acceptance test for T376-T380 shadow audit and backlog.

Exercises the five T376-T380 scripts directly without importing
test_signal_outcome.py or modifying any existing test files.
"""
from __future__ import annotations

import json
from pathlib import Path

# Import the 5 T376-T380 scripts directly
import scripts.audit_shadow_sample_quality as sample_quality_script
import scripts.analyze_readiness_blocker_attribution as blocker_attr_script
import scripts.generate_shadow_collection_plan_v4 as collection_plan_script
import scripts.prioritize_shadow_only_backlog as backlog_prio_script
import scripts.generate_shadow_phase_control_report_v4 as phase_ctrl_v4_script


def test_t376_t380_shadow_audit_and_backlog(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    for folder in [
        "testnet_dry_run_readiness_v4",
        "phase_control_v3",
        "remediation_gap_convergence_v3",
        "shadow_sample_quality",
        "shadow_candidate_outcomes",
        "shadow_sample_quality_audit",
        "readiness_blocker_attribution",
        "shadow_collection_plan_v4",
        "shadow_only_backlog_prioritization",
        "shadow_phase_control_v4",
    ]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    # Fixtures: Upstream outputs (readiness v4, phase control v3, etc.)
    (reports / "testnet_dry_run_readiness_v4" / "testnet_dry_run_readiness_v4_report.json").write_text(
        json.dumps({
            "task_id": "T374",
            "final_verdict": "NOT_READY",
            "readiness_score": 40.0,
            "allow_testnet_dry_run": False,
            "required_gates": {
                "remediation_effective": False,
                "sample_gap_closed": False,
                "convergence_confirmed": False,
                "safety_flags_clean": True,
                "history_dedup_ok": True,
                "shadow_only_integrity_ok": True,
                "multi_round_confirmation_ok": False,
            },
            "blocked_reasons": [
                "remediation_not_effective",
                "sample_gap_remaining_22",
                "convergence_not_confirmed",
                "multi_round_confirmation_not_achieved",
            ],
            "allowed_actions": ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"],
        }),
        encoding="utf-8",
    )
    (reports / "phase_control_v3" / "shadow_phase_control_report_v3.json").write_text(
        json.dumps({
            "task_id": "T375",
            "final_decision": "CONTINUE_SHADOW_ONLY",
            "final_verdict": "PASS",
            "readiness_v4_final_verdict": "NOT_READY",
            "still_not_ready": True,
            "remediation_effective": False,
            "allowed_actions": ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"],
            "archive_range": "T208-T375",
            "next_recommended_task_range": "T376-T380",
        }),
        encoding="utf-8",
    )
    (reports / "remediation_gap_convergence_v3" / "summary.json").write_text(
        json.dumps({
            "task_id": "T373",
            "gap_initial": 22,
            "gap_previous": 22,
            "gap_latest": 22,
            "gap_trend": "FLAT",
            "convergence_confidence": "LOW",
            "runs_analyzed": 3,
            "remediation_effective": False,
            "convergence_confirmed": False,
            "still_not_ready": True,
        }),
        encoding="utf-8",
    )
    (reports / "shadow_sample_quality" / "shadow_sample_quality_dashboard.json").write_text(
        json.dumps({
            "total_samples": 0,
            "unique_samples": 0,
            "duplicate_samples": 0,
            "missing_fields": 0,
            "timestamp_anomalies": 0,
            "symbol_coverage": 0,
            "timeframe_coverage": 0,
            "quality_score": 0.0,
        }),
        encoding="utf-8",
    )
    (reports / "shadow_candidate_outcomes" / "summary.json").write_text(
        json.dumps({
            "shadow_sample_count": 0,
            "weighted_sample_count": 0.0,
        }),
        encoding="utf-8",
    )

    # T376: Shadow sample quality audit
    sample_quality = sample_quality_script.audit_shadow_sample_quality(
        shadow_sample_quality_json=str(reports / "shadow_sample_quality" / "shadow_sample_quality_dashboard.json"),
        shadow_candidate_outcomes_json=str(reports / "shadow_candidate_outcomes" / "summary.json"),
        output_dir=str(reports / "shadow_sample_quality_audit"),
    )
    assert sample_quality["task_id"] == "T376"
    assert sample_quality["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert sample_quality["allowed_mode"] == "SHADOW_ONLY"
    assert sample_quality["submit_permission"] == "NO_SUBMIT"
    assert sample_quality["testnet_submit_allowed"] is False
    assert sample_quality["real_submit_allowed"] is False
    assert sample_quality["submit_attempted"] is False
    assert sample_quality["cancel_attempted"] is False
    assert sample_quality["flatten_attempted"] is False
    assert "samples_analyzed" in sample_quality
    assert "unique_sample_keys" in sample_quality
    assert "duplicate_samples" in sample_quality
    assert "missing_required_fields_count" in sample_quality
    assert "timestamp_anomaly_count" in sample_quality
    assert "symbol_coverage_count" in sample_quality
    assert "timeframe_coverage_count" in sample_quality
    assert "quality_score" in sample_quality
    assert "quality_grade" in sample_quality
    assert "sample_quality_ready" in sample_quality
    assert isinstance(sample_quality["audit_warnings"], list)

    # T377: Readiness blocker attribution
    blocker_attr = blocker_attr_script.analyze_readiness_blocker_attribution(
        readiness_v4_json=str(reports / "testnet_dry_run_readiness_v4" / "testnet_dry_run_readiness_v4_report.json"),
        phase_control_v3_json=str(reports / "phase_control_v3" / "shadow_phase_control_report_v3.json"),
        sample_quality_audit_json=str(reports / "shadow_sample_quality_audit" / "shadow_sample_quality_audit.json"),
        convergence_v3_json=str(reports / "remediation_gap_convergence_v3" / "summary.json"),
        output_dir=str(reports / "readiness_blocker_attribution"),
    )
    assert blocker_attr["task_id"] == "T377"
    assert blocker_attr["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert blocker_attr["allowed_mode"] == "SHADOW_ONLY"
    assert blocker_attr["submit_permission"] == "NO_SUBMIT"
    assert blocker_attr["testnet_submit_allowed"] is False
    assert blocker_attr["real_submit_allowed"] is False
    assert blocker_attr["submit_attempted"] is False
    assert blocker_attr["cancel_attempted"] is False
    assert blocker_attr["flatten_attempted"] is False
    assert "readiness_final_verdict" in blocker_attr
    assert "blocker_count" in blocker_attr
    assert "primary_blocker" in blocker_attr
    assert isinstance(blocker_attr["blockers"], list)
    assert "actionability_score" in blocker_attr
    assert "still_not_ready" in blocker_attr
    assert blocker_attr["still_not_ready"] is True

    # T378: Shadow collection plan v4
    collection_plan = collection_plan_script.generate_shadow_collection_plan_v4(
        blocker_attribution_json=str(reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json"),
        sample_quality_audit_json=str(reports / "shadow_sample_quality_audit" / "shadow_sample_quality_audit.json"),
        phase_control_v3_json=str(reports / "phase_control_v3" / "shadow_phase_control_report_v3.json"),
        output_dir=str(reports / "shadow_collection_plan_v4"),
    )
    assert collection_plan["task_id"] == "T378"
    assert collection_plan["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert collection_plan["allowed_mode"] == "SHADOW_ONLY"
    assert collection_plan["submit_permission"] == "NO_SUBMIT"
    assert collection_plan["testnet_submit_allowed"] is False
    assert collection_plan["real_submit_allowed"] is False
    assert collection_plan["submit_attempted"] is False
    assert collection_plan["cancel_attempted"] is False
    assert collection_plan["flatten_attempted"] is False
    assert collection_plan["plan_version"] == "v4"
    assert "total_target_samples" in collection_plan
    assert isinstance(collection_plan["collection_items"], list)
    assert "minimum_required_new_samples" in collection_plan
    assert isinstance(collection_plan["quality_requirements"], dict)
    assert "plan_ready" in collection_plan
    assert "still_not_ready" in collection_plan
    assert collection_plan["still_not_ready"] is True

    # T379: Shadow only backlog prioritization
    backlog_prio = backlog_prio_script.prioritize_shadow_only_backlog(
        blocker_attribution_json=str(reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json"),
        shadow_collection_plan_v4_json=str(reports / "shadow_collection_plan_v4" / "shadow_collection_plan_v4.json"),
        sample_quality_audit_json=str(reports / "shadow_sample_quality_audit" / "shadow_sample_quality_audit.json"),
        output_dir=str(reports / "shadow_only_backlog_prioritization"),
    )
    assert backlog_prio["task_id"] == "T379"
    assert backlog_prio["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert backlog_prio["allowed_mode"] == "SHADOW_ONLY"
    assert backlog_prio["submit_permission"] == "NO_SUBMIT"
    assert backlog_prio["testnet_submit_allowed"] is False
    assert backlog_prio["real_submit_allowed"] is False
    assert backlog_prio["submit_attempted"] is False
    assert backlog_prio["cancel_attempted"] is False
    assert backlog_prio["flatten_attempted"] is False
    assert "backlog_count" in backlog_prio
    assert "high_priority_count" in backlog_prio
    assert isinstance(backlog_prio["backlog_items"], list)
    assert "top_priority" in backlog_prio
    assert "still_not_ready" in backlog_prio
    assert backlog_prio["still_not_ready"] is True
    # If still_not_ready, must have at least one item that blocks readiness
    if backlog_prio["still_not_ready"] and backlog_prio["backlog_items"]:
        blocks_readiness = any(b.get("blocks_readiness", False) for b in backlog_prio["backlog_items"])
        assert blocks_readiness, "still_not_ready requires at least one backlog item with blocks_readiness=True"

    # T380: Shadow phase control report v4
    phase_ctrl_v4 = phase_ctrl_v4_script.generate_shadow_phase_control_report_v4(
        sample_quality_audit_json=str(reports / "shadow_sample_quality_audit" / "shadow_sample_quality_audit.json"),
        blocker_attribution_json=str(reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json"),
        shadow_collection_plan_v4_json=str(reports / "shadow_collection_plan_v4" / "shadow_collection_plan_v4.json"),
        backlog_prioritization_json=str(reports / "shadow_only_backlog_prioritization" / "shadow_only_backlog_prioritization.json"),
        output_dir=str(reports / "shadow_phase_control_v4"),
    )
    assert phase_ctrl_v4["task_id"] == "T380"
    assert phase_ctrl_v4["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert phase_ctrl_v4["allowed_mode"] == "SHADOW_ONLY"
    assert phase_ctrl_v4["submit_permission"] == "NO_SUBMIT"
    assert phase_ctrl_v4["testnet_submit_allowed"] is False
    assert phase_ctrl_v4["real_submit_allowed"] is False
    assert phase_ctrl_v4["submit_attempted"] is False
    assert phase_ctrl_v4["cancel_attempted"] is False
    assert phase_ctrl_v4["flatten_attempted"] is False
    assert "sample_quality_ready" in phase_ctrl_v4
    assert "primary_blocker" in phase_ctrl_v4
    assert "total_target_samples" in phase_ctrl_v4
    assert "backlog_count" in phase_ctrl_v4
    assert "readiness_status" in phase_ctrl_v4
    assert phase_ctrl_v4["readiness_status"] in {"READY", "NOT_READY", "FAIL", "UNKNOWN"}
    assert phase_ctrl_v4["final_decision"] in {
        "CONTINUE_SHADOW_ONLY",
        "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW",
        "FAIL_SAFE_BLOCK",
    }
    assert isinstance(phase_ctrl_v4["allowed_actions"], list)
    assert "SHADOW_ONLY" in phase_ctrl_v4["allowed_actions"]
    assert isinstance(phase_ctrl_v4["blocked_reasons"], list)
    assert phase_ctrl_v4["archive_range"] == "T208-T380"
    assert phase_ctrl_v4["next_recommended_task_range"] == "T381-T385"

    # NOT_READY case: must have TESTNET_DRY_RUN_BLOCKED and NO TESTNET_DRY_RUN_ONLY
    if phase_ctrl_v4["readiness_status"] == "NOT_READY":
        assert "TESTNET_DRY_RUN_BLOCKED" in phase_ctrl_v4["allowed_actions"]
        assert "TESTNET_DRY_RUN_ONLY" not in phase_ctrl_v4["allowed_actions"]
        assert phase_ctrl_v4["final_decision"] == "CONTINUE_SHADOW_ONLY"

    # Expected outcome for our test fixtures (NOT_READY)
    assert phase_ctrl_v4["final_decision"] == "CONTINUE_SHADOW_ONLY"


def test_t376_sample_quality_with_samples(tmp_path: Path) -> None:
    """Test T376 with actual sample data available."""
    reports = tmp_path / "reports"
    for folder in ["shadow_sample_quality", "shadow_candidate_outcomes", "shadow_sample_quality_audit"]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    (reports / "shadow_sample_quality" / "shadow_sample_quality_dashboard.json").write_text(
        json.dumps({
            "total_samples": 15,
            "unique_samples": 15,
            "duplicate_samples": 0,
            "missing_fields": 0,
            "timestamp_anomalies": 0,
            "symbol_coverage": 2,
            "timeframe_coverage": 2,
            "quality_score": 85.5,
        }),
        encoding="utf-8",
    )
    (reports / "shadow_candidate_outcomes" / "summary.json").write_text(
        json.dumps({
            "shadow_sample_count": 15,
            "weighted_sample_count": 15.0,
        }),
        encoding="utf-8",
    )

    result = sample_quality_script.audit_shadow_sample_quality(
        shadow_sample_quality_json=str(reports / "shadow_sample_quality" / "shadow_sample_quality_dashboard.json"),
        shadow_candidate_outcomes_json=str(reports / "shadow_candidate_outcomes" / "summary.json"),
        output_dir=str(reports / "shadow_sample_quality_audit"),
    )

    assert result["samples_analyzed"] == 15
    assert result["unique_sample_keys"] == 15
    assert result["quality_grade"] in {"GOOD", "FAIR"}
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False


def test_t380_with_sample_quality_ready_but_not_ready_overall(tmp_path: Path) -> None:
    """Test T380 with sample_quality_ready=True but overall still NOT_READY."""
    reports = tmp_path / "reports"
    for folder in [
        "shadow_sample_quality_audit",
        "readiness_blocker_attribution",
        "shadow_collection_plan_v4",
        "shadow_only_backlog_prioritization",
        "shadow_phase_control_v4",
    ]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    # Sample quality is ready but other blockers remain
    (reports / "shadow_sample_quality_audit" / "shadow_sample_quality_audit.json").write_text(
        json.dumps({
            "task_id": "T376",
            "sample_quality_ready": True,
            "samples_analyzed": 20,
            "final_verdict": "PASS",
            "allowed_mode": "SHADOW_ONLY",
            "submit_permission": "NO_SUBMIT",
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        }),
        encoding="utf-8",
    )
    (reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json").write_text(
        json.dumps({
            "task_id": "T377",
            "readiness_final_verdict": "NOT_READY",
            "primary_blocker": "REMEDIATION",
            "still_not_ready": True,
            "final_verdict": "PARTIAL",
            "allowed_mode": "SHADOW_ONLY",
            "submit_permission": "NO_SUBMIT",
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        }),
        encoding="utf-8",
    )
    (reports / "shadow_collection_plan_v4" / "shadow_collection_plan_v4.json").write_text(
        json.dumps({
            "task_id": "T378",
            "plan_version": "v4",
            "total_target_samples": 10,
            "still_not_ready": True,
            "final_verdict": "PASS",
            "allowed_mode": "SHADOW_ONLY",
            "submit_permission": "NO_SUBMIT",
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        }),
        encoding="utf-8",
    )
    (reports / "shadow_only_backlog_prioritization" / "shadow_only_backlog_prioritization.json").write_text(
        json.dumps({
            "task_id": "T379",
            "backlog_count": 2,
            "high_priority_count": 1,
            "top_priority": "READINESS",
            "still_not_ready": True,
            "final_verdict": "PASS",
            "allowed_mode": "SHADOW_ONLY",
            "submit_permission": "NO_SUBMIT",
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        }),
        encoding="utf-8",
    )

    result = phase_ctrl_v4_script.generate_shadow_phase_control_report_v4(
        sample_quality_audit_json=str(reports / "shadow_sample_quality_audit" / "shadow_sample_quality_audit.json"),
        blocker_attribution_json=str(reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json"),
        shadow_collection_plan_v4_json=str(reports / "shadow_collection_plan_v4" / "shadow_collection_plan_v4.json"),
        backlog_prioritization_json=str(reports / "shadow_only_backlog_prioritization" / "shadow_only_backlog_prioritization.json"),
        output_dir=str(reports / "shadow_phase_control_v4"),
    )

    assert result["sample_quality_ready"] is True
    assert result["readiness_status"] == "NOT_READY"
    assert result["final_decision"] == "CONTINUE_SHADOW_ONLY"
    assert "TESTNET_DRY_RUN_BLOCKED" in result["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in result["allowed_actions"]
    assert result["testnet_submit_allowed"] is False
    assert result["real_submit_allowed"] is False
    assert result["archive_range"] == "T208-T380"
    assert result["next_recommended_task_range"] == "T381-T385"


def test_t377_t379_with_sample_quality_not_ready_produces_blocker(tmp_path: Path) -> None:
    """Test that sample_quality_ready=False produces SAMPLE_QUALITY blocker/backlog."""
    reports = tmp_path / "reports"
    for folder in [
        "testnet_dry_run_readiness_v4",
        "phase_control_v3",
        "remediation_gap_convergence_v3",
        "shadow_sample_quality_audit",
        "readiness_blocker_attribution",
        "shadow_collection_plan_v4",
        "shadow_only_backlog_prioritization",
    ]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    (reports / "testnet_dry_run_readiness_v4" / "testnet_dry_run_readiness_v4_report.json").write_text(
        json.dumps({
            "task_id": "T374",
            "final_verdict": "NOT_READY",
            "required_gates": {"safety_flags_clean": True},
            "blocked_reasons": [],
        }),
        encoding="utf-8",
    )
    (reports / "phase_control_v3" / "shadow_phase_control_report_v3.json").write_text(json.dumps({}))
    (reports / "remediation_gap_convergence_v3" / "summary.json").write_text(json.dumps({}))
    (reports / "shadow_sample_quality_audit" / "shadow_sample_quality_audit.json").write_text(
        json.dumps({
            "task_id": "T376",
            "sample_quality_ready": False,
            "final_verdict": "PARTIAL",
            "allowed_mode": "SHADOW_ONLY",
            "submit_permission": "NO_SUBMIT",
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
        }),
        encoding="utf-8",
    )

    blocker_attr = blocker_attr_script.analyze_readiness_blocker_attribution(
        readiness_v4_json=str(reports / "testnet_dry_run_readiness_v4" / "testnet_dry_run_readiness_v4_report.json"),
        phase_control_v3_json=str(reports / "phase_control_v3" / "shadow_phase_control_report_v3.json"),
        sample_quality_audit_json=str(reports / "shadow_sample_quality_audit" / "shadow_sample_quality_audit.json"),
        convergence_v3_json=str(reports / "remediation_gap_convergence_v3" / "summary.json"),
        output_dir=str(reports / "readiness_blocker_attribution"),
    )

    # Should have SAMPLE_QUALITY as a blocker
    has_sample_quality_blocker = any(
        "SAMPLE_QUALITY" in b.get("code", "") or b.get("code") == "SAMPLE_QUALITY_NOT_READY"
        for b in blocker_attr["blockers"]
    )
    # Either in code or primary_blocker
    assert has_sample_quality_blocker or blocker_attr["primary_blocker"] in {"SAMPLE", "SAMPLE_QUALITY"}

    # Now generate backlog from this
    collection_plan = collection_plan_script.generate_shadow_collection_plan_v4(
        blocker_attribution_json=str(reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json"),
        sample_quality_audit_json=str(reports / "shadow_sample_quality_audit" / "shadow_sample_quality_audit.json"),
        phase_control_v3_json=str(reports / "phase_control_v3" / "shadow_phase_control_report_v3.json"),
        output_dir=str(reports / "shadow_collection_plan_v4"),
    )
    backlog_prio = backlog_prio_script.prioritize_shadow_only_backlog(
        blocker_attribution_json=str(reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json"),
        shadow_collection_plan_v4_json=str(reports / "shadow_collection_plan_v4" / "shadow_collection_plan_v4.json"),
        sample_quality_audit_json=str(reports / "shadow_sample_quality_audit" / "shadow_sample_quality_audit.json"),
        output_dir=str(reports / "shadow_only_backlog_prioritization"),
    )

    assert backlog_prio["backlog_count"] >= 1
    assert backlog_prio["still_not_ready"] is True
    assert backlog_prio["testnet_submit_allowed"] is False
    assert backlog_prio["real_submit_allowed"] is False


def test_scripts_support_json_flag() -> None:
    """Verify all scripts support --json flag (by checking arg parser)."""
    # Just check that parsers have --json option
    sample_quality_parser = sample_quality_script.build_arg_parser()
    blocker_attr_parser = blocker_attr_script.build_arg_parser()
    collection_plan_parser = collection_plan_script.build_arg_parser()
    backlog_prio_parser = backlog_prio_script.build_arg_parser()
    phase_ctrl_v4_parser = phase_ctrl_v4_script.build_arg_parser()

    # All should have --json option
    sample_quality_actions = [a.dest for a in sample_quality_parser._actions]
    blocker_attr_actions = [a.dest for a in blocker_attr_parser._actions]
    collection_plan_actions = [a.dest for a in collection_plan_parser._actions]
    backlog_prio_actions = [a.dest for a in backlog_prio_parser._actions]
    phase_ctrl_v4_actions = [a.dest for a in phase_ctrl_v4_parser._actions]

    assert "json" in sample_quality_actions
    assert "json" in blocker_attr_actions
    assert "json" in collection_plan_actions
    assert "json" in backlog_prio_actions
    assert "json" in phase_ctrl_v4_actions
