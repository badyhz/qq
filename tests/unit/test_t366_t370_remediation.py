"""Targeted acceptance test for T366-T370 remediation round 2.

This is a focused alternative test because the main test_signal_outcome.py
cannot be collected due to cascading import errors from unrelated core modules.
It exercises the same logic as test_t366_t370_second_remediation_and_decision_v2_pipeline
but imports only the 5 T366-T370 scripts directly."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _write_csv_from_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# Import the 5 T366-T370 scripts directly
import scripts.run_second_remediation_shadow_loop as second_remediation_script
import scripts.analyze_remediation_gap_convergence_v2 as gap_convergence_v2_script
import scripts.allocate_shadow_sample_targets_v2 as sample_targets_v2_script
import scripts.generate_testnet_dry_run_readiness_v3 as readiness_v3_script
import scripts.generate_shadow_to_dry_run_decision_report_v2 as decision_v2_script


def test_t366_t370_second_remediation_and_decision_v2_pipeline(tmp_path: Path):
    reports = tmp_path / "reports"
    for folder in [
        "remediation_loop_packet",
        "remediation_loop_history",
        "remediation_loop_run",
        "second_remediation_loop",
        "remediation_gap_convergence",
        "remediation_gap_convergence_v2",
        "shadow_sample_targets",
        "shadow_sample_targets_v2",
        "testnet_dry_run_readiness_v2",
        "testnet_dry_run_readiness_v3",
        "shadow_to_dry_run_decision",
        "shadow_to_dry_run_decision_v2",
        "phase_control",
        "daily_shadow_research_control",
        "next_shadow_experiment_run_plan",
        "shadow_candidate_collection",
        "shadow_candidate_outcomes",
        "next_shadow_experiment_run",
    ]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    # Set up shared input fixtures
    (reports / "remediation_loop_packet" / "remediation_loop_packet.json").write_text(
        json.dumps({"commands": [{"step":1,"name":"noop_step","action_type":"REPORT_ONLY","command":"echo ok","expected_outputs":[],"stop_on_failure":True}]}),
        encoding="utf-8",
    )
    (reports / "remediation_loop_history" / "remediation_loop_history.csv").write_text(
        "run_id,sample_gap_before,sample_gap_after,gap_delta,submit_attempted\n"
        "R1,22,20,-2,false\n"
        "R2,20,18,-2,false\n",
        encoding="utf-8",
    )
    (reports / "remediation_loop_run" / "remediation_loop_run_report.json").write_text(
        json.dumps({"final_verdict":"PARTIAL","sample_gap_after":18,"remediation_effective":True,"allowed_mode":"SHADOW_ONLY"}),
        encoding="utf-8",
    )
    (reports / "daily_shadow_research_control" / "daily_shadow_research_control_report.json").write_text(
        json.dumps({"sample_gap_total":18,"total_experiments":3,"next_run_candidate_count":3}),
        encoding="utf-8",
    )
    (reports / "shadow_candidate_collection" / "summary.json").write_text(
        json.dumps({"collected_count":8}),
        encoding="utf-8",
    )
    (reports / "shadow_candidate_outcomes" / "summary.json").write_text(
        json.dumps({"shadow_sample_count":8,"weighted_sample_count":2.5}),
        encoding="utf-8",
    )
    (reports / "next_shadow_experiment_run" / "summary.json").write_text(
        json.dumps({"next_run_candidate_count":3}),
        encoding="utf-8",
    )
    (reports / "phase_control" / "phase_control_report_v2.json").write_text(
        json.dumps({"final_verdict":"SHADOW_ONLY_CONTINUE","current_phase":"SHADOW_EXPERIMENT_REMEDIATION"}),
        encoding="utf-8",
    )

    # T366: Second remediation shadow loop
    (reports / "shadow_sample_targets" / "summary.json").write_text(
        json.dumps({"allocation_strategy":"STANDARD","final_allocation":12}),
        encoding="utf-8",
    )
    second_loop = second_remediation_script.run_second_remediation_shadow_loop(
        remediation_loop_packet_json=str(reports / "remediation_loop_packet" / "remediation_loop_packet.json"),
        remediation_history_csv=str(reports / "remediation_loop_history" / "remediation_loop_history.csv"),
        first_loop_report_json=str(reports / "remediation_loop_run" / "remediation_loop_run_report.json"),
        shadow_outcomes_summary_json=str(reports / "shadow_candidate_outcomes" / "summary.json"),
        sample_targets_summary_json=str(reports / "shadow_sample_targets" / "summary.json"),
        output_dir=str(reports / "second_remediation_loop"),
    )
    assert second_loop["task_id"] == "T366"
    assert second_loop["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert second_loop["allowed_mode"] == "SHADOW_ONLY"
    assert second_loop["submit_permission"] == "NO_SUBMIT"
    assert second_loop["testnet_submit_allowed"] is False
    assert second_loop["real_submit_allowed"] is False
    assert second_loop["submit_attempted"] is False
    assert second_loop["cancel_attempted"] is False
    assert second_loop["flatten_attempted"] is False
    assert second_loop["still_not_ready"] is True
    assert second_loop["source_history_runs"] >= 1

    # T367: Remediation gap convergence v2
    (reports / "remediation_gap_convergence" / "summary.json").write_text(
        json.dumps({"current_sample_gap":18,"final_verdict":"CONVERGING","gap_trend_slope":-2.0}),
        encoding="utf-8",
    )
    (reports / "shadow_sample_targets" / "summary.json").write_text(
        json.dumps({"allocation_strategy":"STANDARD","final_allocation":12}),
        encoding="utf-8",
    )
    conv_v2 = gap_convergence_v2_script.analyze_remediation_gap_convergence_v2(
        remediation_history_csv=str(reports / "remediation_loop_history" / "remediation_loop_history.csv"),
        second_loop_report_json=str(reports / "second_remediation_loop" / "second_remediation_loop_report.json"),
        first_convergence_summary_json=str(reports / "remediation_gap_convergence" / "summary.json"),
        sample_targets_summary_json=str(reports / "shadow_sample_targets" / "summary.json"),
        output_dir=str(reports / "remediation_gap_convergence_v2"),
    )
    assert conv_v2["task_id"] == "T367"
    assert conv_v2["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert conv_v2["allowed_mode"] == "SHADOW_ONLY"
    assert conv_v2["submit_permission"] == "NO_SUBMIT"
    assert conv_v2["testnet_submit_allowed"] is False
    assert conv_v2["real_submit_allowed"] is False
    assert conv_v2["submit_attempted"] is False
    assert conv_v2["cancel_attempted"] is False
    assert conv_v2["flatten_attempted"] is False
    assert conv_v2["runs_analyzed"] >= 1
    assert conv_v2["gap_trend"] in {"UNKNOWN", "IMPROVING", "FLAT", "WORSENING"}
    assert conv_v2["convergence_confidence"] in {"LOW", "MEDIUM", "HIGH"}
    if conv_v2["gap_latest"] > 0:
        assert conv_v2["still_not_ready"] is True

    # T368: Shadow sample targets v2
    _write_csv_from_rows(
        reports / "next_shadow_experiment_run_plan" / "next_shadow_experiment_run_plan.csv",
        [
            {"experiment_key":"exp_v2_001","symbol":"BTCUSDT","timeframe":"1h","setup":"LONG","current_samples":5},
            {"experiment_key":"exp_v2_002","symbol":"ETHUSDT","timeframe":"1h","setup":"SHORT","current_samples":3},
        ],
    )
    (reports / "shadow_candidate_outcomes" / "summary.json").write_text(
        json.dumps({"shadow_sample_count":8,"weighted_sample_count":2.5}),
        encoding="utf-8",
    )
    alloc_v2 = sample_targets_v2_script.allocate_shadow_sample_targets_v2(
        convergence_v2_summary_json=str(reports / "remediation_gap_convergence_v2" / "summary.json"),
        previous_targets_summary_json=str(reports / "shadow_sample_targets" / "summary.json"),
        shadow_outcomes_summary_json=str(reports / "shadow_candidate_outcomes" / "summary.json"),
        next_run_plan_csv=str(reports / "next_shadow_experiment_run_plan" / "next_shadow_experiment_run_plan.csv"),
        output_dir=str(reports / "shadow_sample_targets_v2"),
    )
    assert alloc_v2["task_id"] == "T368"
    assert alloc_v2["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert alloc_v2["allowed_mode"] == "SHADOW_ONLY"
    assert alloc_v2["submit_permission"] == "NO_SUBMIT"
    assert alloc_v2["testnet_submit_allowed"] is False
    assert alloc_v2["real_submit_allowed"] is False
    assert alloc_v2["submit_attempted"] is False
    assert alloc_v2["cancel_attempted"] is False
    assert alloc_v2["flatten_attempted"] is False
    assert alloc_v2["allocation_strategy"] in {"GAP_WEIGHTED", "EVEN", "FALLBACK"}
    assert alloc_v2["total_allocated_target_samples_next_run"] >= 0
    assert alloc_v2["allocations"] is not None
    assert len(alloc_v2["allocations"]) >= 1
    for alloc_item in alloc_v2["allocations"]:
        assert "submit" not in str(alloc_item.get("reason", "")).lower()
        assert "cancel" not in str(alloc_item.get("reason", "")).lower()

    # T369: Testnet dry-run readiness v3
    (reports / "testnet_dry_run_readiness_v2" / "testnet_dry_run_readiness_v2_report.json").write_text(
        json.dumps({"final_verdict":"NOT_READY","readiness_score":40.0,"allow_testnet_dry_run":False}),
        encoding="utf-8",
    )
    readiness_v3 = readiness_v3_script.generate_testnet_dry_run_readiness_v3(
        second_loop_report_json=str(reports / "second_remediation_loop" / "second_remediation_loop_report.json"),
        convergence_v2_summary_json=str(reports / "remediation_gap_convergence_v2" / "summary.json"),
        allocator_v2_summary_json=str(reports / "shadow_sample_targets_v2" / "summary.json"),
        readiness_v2_report_json=str(reports / "testnet_dry_run_readiness_v2" / "testnet_dry_run_readiness_v2_report.json"),
        phase_control_json=str(reports / "phase_control" / "phase_control_report_v2.json"),
        output_dir=str(reports / "testnet_dry_run_readiness_v3"),
    )
    assert readiness_v3["task_id"] == "T369"
    assert readiness_v3["final_verdict"] in {"READY", "NOT_READY", "FAIL"}
    assert readiness_v3["allowed_mode"] == "SHADOW_ONLY"
    assert readiness_v3["submit_permission"] == "NO_SUBMIT"
    assert readiness_v3["testnet_submit_allowed"] is False
    assert readiness_v3["real_submit_allowed"] is False
    assert readiness_v3["submit_attempted"] is False
    assert readiness_v3["cancel_attempted"] is False
    assert readiness_v3["flatten_attempted"] is False
    assert readiness_v3["readiness_trend"] in {"IMPROVING", "FLAT", "WORSENING", "UNKNOWN"}
    assert readiness_v3["readiness_score"] >= 0.0
    assert "SHADOW_ONLY" in readiness_v3["allowed_actions"]
    if not readiness_v3["allow_testnet_dry_run"]:
        assert "TESTNET_DRY_RUN_ONLY" not in readiness_v3["allowed_actions"]
        assert "TESTNET_DRY_RUN_BLOCKED" in readiness_v3["allowed_actions"]
    gates = readiness_v3["required_gates"]
    assert "remediation_effective" in gates
    assert "sample_gap_closed" in gates
    assert "convergence_confirmed" in gates
    assert "safety_flags_clean" in gates

    # T370: Shadow to dry-run decision v2
    (reports / "shadow_to_dry_run_decision" / "shadow_to_dry_run_decision_report.json").write_text(
        json.dumps({"final_verdict":"SHADOW_ONLY_CONTINUE","decision":"CONTINUE_SHADOW_ONLY_UNTIL_CONVERGENCE"}),
        encoding="utf-8",
    )
    decision_v2 = decision_v2_script.generate_shadow_to_dry_run_decision_report_v2(
        readiness_v3_report_json=str(reports / "testnet_dry_run_readiness_v3" / "testnet_dry_run_readiness_v3_report.json"),
        convergence_v2_summary_json=str(reports / "remediation_gap_convergence_v2" / "summary.json"),
        allocator_v2_summary_json=str(reports / "shadow_sample_targets_v2" / "summary.json"),
        decision_v1_report_json=str(reports / "shadow_to_dry_run_decision" / "shadow_to_dry_run_decision_report.json"),
        phase_control_json=str(reports / "phase_control" / "phase_control_report_v2.json"),
        output_dir=str(reports / "shadow_to_dry_run_decision_v2"),
    )
    assert decision_v2["task_id"] == "T370"
    assert decision_v2["final_verdict"] in {"PASS", "PARTIAL", "FAIL"}
    assert decision_v2["allowed_mode"] == "SHADOW_ONLY"
    assert decision_v2["submit_permission"] == "NO_SUBMIT"
    assert decision_v2["testnet_submit_allowed"] is False
    assert decision_v2["real_submit_allowed"] is False
    assert decision_v2["submit_attempted"] is False
    assert decision_v2["cancel_attempted"] is False
    assert decision_v2["flatten_attempted"] is False
    assert decision_v2["final_decision"] in {"CONTINUE_SHADOW_ONLY","READY_FOR_MANUAL_TESTNET_DRY_RUN_REVIEW","FAIL_SAFE_BLOCK"}
    assert decision_v2["archive_range"] == "T208-T370"
    assert decision_v2["next_recommended_task_range"] == "T371-T375"
    assert "SHADOW_ONLY" in decision_v2["allowed_actions"]
    if decision_v2["final_decision"] == "CONTINUE_SHADOW_ONLY":
        assert "TESTNET_DRY_RUN_BLOCKED" in decision_v2["allowed_actions"]
        assert "TESTNET_DRY_RUN_ONLY" not in decision_v2["allowed_actions"]
    assert decision_v2["still_not_ready"] is True
    assert decision_v2["testnet_submit_allowed"] is False
    assert decision_v2["real_submit_allowed"] is False
