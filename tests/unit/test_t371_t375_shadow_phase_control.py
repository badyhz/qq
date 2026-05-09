"""Targeted acceptance test for T371-T375 shadow phase control round 3.

Exercises the five T371-T375 scripts directly without importing
test_signal_outcome.py or modifying any existing test files."""
from __future__ import annotations

import json
from pathlib import Path

# Import the 5 T371-T375 scripts directly
import scripts.generate_remediation_loop_packet_v3 as packet_v3_script
import scripts.run_third_remediation_shadow_loop as third_remediation_script
import scripts.analyze_remediation_gap_convergence_v3 as convergence_v3_script
import scripts.generate_testnet_dry_run_readiness_v4 as readiness_v4_script
import scripts.generate_shadow_phase_control_report_v3 as phase_control_v3_script


def test_t371_t375_shadow_phase_control_v3_pipeline(tmp_path: Path):
    reports = tmp_path / "reports"
    for folder in [
        "shadow_to_dry_run_decision_v2",
        "testnet_dry_run_readiness_v3",
        "remediation_gap_convergence_v2",
        "phase_control",
        "shadow_candidate_outcomes",
        "daily_shadow_research_control",
        "remediation_loop_packet_v3",
        "third_remediation_loop",
        "remediation_gap_convergence_v3",
        "testnet_dry_run_readiness_v4",
        "phase_control_v3",
        "second_remediation_loop",
    ]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    # Fixtures: T366-T370 upstream outputs
    (reports / "shadow_to_dry_run_decision_v2" / "shadow_to_dry_run_decision_v2_report.json").write_text(
        json.dumps({
            "task_id": "T370",
            "final_decision": "CONTINUE_SHADOW_ONLY",
            "final_verdict": "PASS",
            "readiness_v3_final_verdict": "NOT_READY",
            "still_not_ready": True,
            "remediation_effective": False,
            "allowed_actions": ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"],
            "archive_range": "T208-T370",
            "next_recommended_task_range": "T371-T375",
        }),
        encoding="utf-8",
    )
    (reports / "testnet_dry_run_readiness_v3" / "testnet_dry_run_readiness_v3_report.json").write_text(
        json.dumps({
            "task_id": "T369",
            "final_verdict": "NOT_READY",
            "readiness_score": 40.0,
            "allow_testnet_dry_run": False,
            "remediation_effective": False,
            "required_gates": {
                "remediation_effective": False,
                "sample_gap_closed": False,
                "convergence_confirmed": False,
                "safety_flags_clean": True,
                "history_dedup_ok": True,
                "shadow_only_integrity_ok": True,
            },
            "blocked_reasons": ["remediation_not_effective", "sample_gap_remaining_22", "convergence_not_confirmed"],
        }),
        encoding="utf-8",
    )
    (reports / "remediation_gap_convergence_v2" / "summary.json").write_text(
        json.dumps({
            "task_id": "T367",
            "gap_initial": 22,
            "gap_previous": 22,
            "gap_latest": 22,
            "gap_delta_latest": 0,
            "gap_series": [22, 22],
            "gap_trend": "FLAT",
            "convergence_confidence": "LOW",
            "runs_analyzed": 2,
            "remediation_effective": False,
            "still_not_ready": True,
        }),
        encoding="utf-8",
    )
    (reports / "phase_control" / "phase_control_report_v2.json").write_text(
        json.dumps({
            "final_verdict": "SHADOW_ONLY_CONTINUE",
            "current_phase": "SHADOW_EXPERIMENT_REMEDIATION",
        }),
        encoding="utf-8",
    )
    (reports / "shadow_candidate_outcomes" / "summary.json").write_text(
        json.dumps({"shadow_sample_count": 0, "weighted_sample_count": 0.0}),
        encoding="utf-8",
    )
    (reports / "daily_shadow_research_control" / "daily_shadow_research_control_report.json").write_text(
        json.dumps({"sample_gap_total": 22, "total_experiments": 3, "next_run_candidate_count": 2}),
        encoding="utf-8",
    )
    (reports / "second_remediation_loop" / "second_remediation_loop_report.json").write_text(
        json.dumps({
            "task_id": "T366",
            "sample_gap_before": 22,
            "sample_gap_after": 22,
            "source_history_runs": 2,
            "remediation_effective": False,
            "still_not_ready": True,
        }),
        encoding="utf-8",
    )

    # T371: Remediation loop packet v3
    packet_v3 = packet_v3_script.generate_remediation_loop_packet_v3(
        decision_v2_json=str(reports / "shadow_to_dry_run_decision_v2" / "shadow_to_dry_run_decision_v2_report.json"),
        readiness_v3_json=str(reports / "testnet_dry_run_readiness_v3" / "testnet_dry_run_readiness_v3_report.json"),
        convergence_v2_json=str(reports / "remediation_gap_convergence_v2" / "summary.json"),
        phase_control_v2_json=str(reports / "phase_control" / "phase_control_report_v2.json"),
        output_dir=str(reports / "remediation_loop_packet_v3"),
    )
    assert packet_v3["task_id"] == "T371"
    assert packet_v3["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert packet_v3["allowed_mode"] == "SHADOW_ONLY"
    assert packet_v3["submit_permission"] == "NO_SUBMIT"
    assert packet_v3["testnet_submit_allowed"] is False
    assert packet_v3["real_submit_allowed"] is False
    assert packet_v3["submit_attempted"] is False
    assert packet_v3["cancel_attempted"] is False
    assert packet_v3["flatten_attempted"] is False
    assert packet_v3["previous_decision"] == "CONTINUE_SHADOW_ONLY"
    assert packet_v3["previous_readiness_verdict"] == "NOT_READY"
    assert packet_v3["packet_ready"] is True
    assert packet_v3["source_archive_range"] == "T208-T370"

    # T372: Third remediation shadow loop
    third_loop = third_remediation_script.run_third_remediation_shadow_loop(
        remediation_loop_packet_v3_json=str(reports / "remediation_loop_packet_v3" / "remediation_loop_packet_v3.json"),
        second_loop_report_json=str(reports / "second_remediation_loop" / "second_remediation_loop_report.json"),
        shadow_outcomes_summary_json=str(reports / "shadow_candidate_outcomes" / "summary.json"),
        shadow_research_control_json=str(reports / "daily_shadow_research_control" / "daily_shadow_research_control_report.json"),
        output_dir=str(reports / "third_remediation_loop"),
    )
    assert third_loop["task_id"] == "T372"
    assert third_loop["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert third_loop["allowed_mode"] == "SHADOW_ONLY"
    assert third_loop["submit_permission"] == "NO_SUBMIT"
    assert third_loop["testnet_submit_allowed"] is False
    assert third_loop["real_submit_allowed"] is False
    assert third_loop["submit_attempted"] is False
    assert third_loop["cancel_attempted"] is False
    assert third_loop["flatten_attempted"] is False
    assert third_loop["remediation_effective"] is False
    assert third_loop["still_not_ready"] is True
    assert third_loop["sample_gap_before"] == 22
    assert third_loop["sample_gap_after"] == 22
    assert third_loop["gap_delta"] == 0
    assert "THIRD_REMEDIATION_" in third_loop["third_loop_run_id"]

    # T373: Remediation gap convergence v3
    conv_v3 = convergence_v3_script.analyze_remediation_gap_convergence_v3(
        convergence_v2_json=str(reports / "remediation_gap_convergence_v2" / "summary.json"),
        third_loop_report_json=str(reports / "third_remediation_loop" / "third_remediation_loop_report.json"),
        second_loop_report_json=str(reports / "second_remediation_loop" / "second_remediation_loop_report.json"),
        remediation_loop_packet_v3_json=str(reports / "remediation_loop_packet_v3" / "remediation_loop_packet_v3.json"),
        output_dir=str(reports / "remediation_gap_convergence_v3"),
    )
    assert conv_v3["task_id"] == "T373"
    assert conv_v3["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert conv_v3["allowed_mode"] == "SHADOW_ONLY"
    assert conv_v3["submit_permission"] == "NO_SUBMIT"
    assert conv_v3["testnet_submit_allowed"] is False
    assert conv_v3["real_submit_allowed"] is False
    assert conv_v3["submit_attempted"] is False
    assert conv_v3["cancel_attempted"] is False
    assert conv_v3["flatten_attempted"] is False
    assert conv_v3["runs_analyzed"] >= 1
    assert conv_v3["gap_trend"] in {"UNKNOWN", "IMPROVING", "FLAT", "WORSENING"}
    assert conv_v3["convergence_confidence"] in {"LOW", "MEDIUM", "HIGH"}
    assert conv_v3["convergence_confirmed"] is False
    assert conv_v3["remediation_effective"] is False
    if conv_v3["gap_latest"] is not None and conv_v3["gap_latest"] > 0:
        assert conv_v3["still_not_ready"] is True
    # gap_latest must not be HIGH unless runs_analyzed >= 5
    if conv_v3["runs_analyzed"] < 5:
        assert conv_v3["convergence_confidence"] != "HIGH"

    # T374: Testnet dry-run readiness v4
    readiness_v4 = readiness_v4_script.generate_testnet_dry_run_readiness_v4(
        convergence_v3_json=str(reports / "remediation_gap_convergence_v3" / "summary.json"),
        third_loop_report_json=str(reports / "third_remediation_loop" / "third_remediation_loop_report.json"),
        readiness_v3_json=str(reports / "testnet_dry_run_readiness_v3" / "testnet_dry_run_readiness_v3_report.json"),
        convergence_v2_json=str(reports / "remediation_gap_convergence_v2" / "summary.json"),
        output_dir=str(reports / "testnet_dry_run_readiness_v4"),
    )
    assert readiness_v4["task_id"] == "T374"
    assert readiness_v4["final_verdict"] in {"READY", "NOT_READY", "FAIL"}
    assert readiness_v4["allowed_mode"] == "SHADOW_ONLY"
    assert readiness_v4["submit_permission"] == "NO_SUBMIT"
    assert readiness_v4["testnet_submit_allowed"] is False
    assert readiness_v4["real_submit_allowed"] is False
    assert readiness_v4["submit_attempted"] is False
    assert readiness_v4["cancel_attempted"] is False
    assert readiness_v4["flatten_attempted"] is False
    assert readiness_v4["allow_testnet_dry_run"] is False
    assert readiness_v4["readiness_trend"] in {"IMPROVING", "FLAT", "WORSENING", "UNKNOWN"}
    assert readiness_v4["readiness_score"] >= 0.0
    assert "SHADOW_ONLY" in readiness_v4["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in readiness_v4["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in readiness_v4["allowed_actions"]
    gates = readiness_v4["required_gates"]
    assert "remediation_effective" in gates
    assert "sample_gap_closed" in gates
    assert "convergence_confirmed" in gates
    assert "safety_flags_clean" in gates
    assert "history_dedup_ok" in gates
    assert "shadow_only_integrity_ok" in gates
    assert "multi_round_confirmation_ok" in gates
    assert gates["safety_flags_clean"] is True
    assert readiness_v4["final_verdict"] == "NOT_READY"

    # T375: Shadow phase control report v3
    phase_ctrl_v3 = phase_control_v3_script.generate_shadow_phase_control_report_v3(
        readiness_v4_json=str(reports / "testnet_dry_run_readiness_v4" / "testnet_dry_run_readiness_v4_report.json"),
        convergence_v3_json=str(reports / "remediation_gap_convergence_v3" / "summary.json"),
        third_loop_report_json=str(reports / "third_remediation_loop" / "third_remediation_loop_report.json"),
        phase_control_v2_json=str(reports / "phase_control" / "phase_control_report_v2.json"),
        output_dir=str(reports / "phase_control_v3"),
    )
    assert phase_ctrl_v3["task_id"] == "T375"
    assert phase_ctrl_v3["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert phase_ctrl_v3["allowed_mode"] == "SHADOW_ONLY"
    assert phase_ctrl_v3["submit_permission"] == "NO_SUBMIT"
    assert phase_ctrl_v3["testnet_submit_allowed"] is False
    assert phase_ctrl_v3["real_submit_allowed"] is False
    assert phase_ctrl_v3["submit_attempted"] is False
    assert phase_ctrl_v3["cancel_attempted"] is False
    assert phase_ctrl_v3["flatten_attempted"] is False
    assert phase_ctrl_v3["final_decision"] in {"CONTINUE_SHADOW_ONLY", "READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW", "FAIL_SAFE_BLOCK"}
    assert phase_ctrl_v3["archive_range"] == "T208-T375"
    assert phase_ctrl_v3["next_recommended_task_range"] == "T376-T380"
    assert "SHADOW_ONLY" in phase_ctrl_v3["allowed_actions"]
    assert phase_ctrl_v3["final_decision"] == "CONTINUE_SHADOW_ONLY"
    assert "TESTNET_DRY_RUN_BLOCKED" in phase_ctrl_v3["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in phase_ctrl_v3["allowed_actions"]
    assert phase_ctrl_v3["still_not_ready"] is True
    assert phase_ctrl_v3["readiness_v4_final_verdict"] == "NOT_READY"
    assert phase_ctrl_v3["testnet_submit_allowed"] is False
    assert phase_ctrl_v3["real_submit_allowed"] is False
