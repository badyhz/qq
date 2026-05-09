"""Targeted acceptance test for T381-T385 shadow collection preflight.

Exercises the five T381-T385 scripts directly without importing
test_signal_outcome.py or modifying any existing test files.
"""
from __future__ import annotations

import json
from pathlib import Path

import scripts.generate_shadow_collection_queue_v1 as queue_v1
import scripts.generate_shadow_data_quality_rules_v1 as rules_v1
import scripts.map_readiness_blockers_to_actions as blocker_map
import scripts.generate_shadow_collection_preflight_v1 as preflight_v1
import scripts.generate_shadow_phase_control_report_v5 as phase_control_v5


def test_t381_t385_shadow_collection_preflight(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    for folder in [
        "shadow_collection_plan_v4",
        "shadow_sample_quality_audit",
        "readiness_blocker_attribution",
        "shadow_only_backlog_prioritization",
        "testnet_dry_run_readiness_v4",
        "shadow_collection_queue_v1",
        "shadow_data_quality_rules_v1",
        "readiness_blocker_to_action_map_v1",
        "shadow_collection_preflight_v1",
        "shadow_phase_control_v5",
    ]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    (reports / "shadow_collection_plan_v4" / "shadow_collection_plan_v4.json").write_text(
        json.dumps({
            "task_id": "T378",
            "plan_version": "v4",
            "total_target_samples": 26,
            "collection_items": [
                {
                    "symbol": "BTCUSDT",
                    "timeframe": "4h",
                    "setup": "quality_improvement",
                    "target_samples": 3,
                    "priority": "HIGH",
                    "reason": "improve_sample_quality",
                },
                {
                    "symbol": "BTCUSDT",
                    "timeframe": "1h",
                    "setup": "remediation_focus",
                    "target_samples": 8,
                    "priority": "HIGH",
                    "reason": "improve_remediation_effectiveness",
                },
            ],
            "plan_ready": True,
            "still_not_ready": True,
        }),
        encoding="utf-8",
    )

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

    (reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json").write_text(
        json.dumps({
            "task_id": "T377",
            "readiness_final_verdict": "NOT_READY",
            "primary_blocker": "REMEDIATION",
            "still_not_ready": True,
            "blockers": [
                {
                    "code": "SAMPLE_QUALITY_NOT_READY",
                    "severity": "HIGH",
                    "actionable": True,
                    "recommended_action": "improve_shadow_sample_quality",
                },
                {
                    "code": "REMEDIATION_NOT_EFFECTIVE",
                    "severity": "HIGH",
                    "actionable": True,
                    "recommended_action": "run_additional_remediation_loops",
                },
            ],
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
            "high_priority_count": 2,
            "top_priority": "DATA_QUALITY",
            "backlog_items": [
                {
                    "id": "BACKLOG-001",
                    "title": "SAMPLE_QUALITY_NOT_READY",
                    "category": "DATA_QUALITY",
                    "priority": "HIGH",
                    "blocks_readiness": True,
                    "recommended_task_range": "T381-T385",
                    "acceptance_hint": "resolve_sample_quality",
                },
            ],
            "still_not_ready": True,
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
            },
            "blocked_reasons": ["remediation_not_effective"],
            "allowed_actions": ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"],
        }),
        encoding="utf-8",
    )

    t381 = queue_v1.generate_shadow_collection_queue_v1(
        shadow_collection_plan_v4_json=str(reports / "shadow_collection_plan_v4" / "shadow_collection_plan_v4.json"),
        output_dir=str(reports / "shadow_collection_queue_v1"),
    )
    assert t381["task_id"] == "T381"
    assert t381["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t381["allowed_mode"] == "SHADOW_ONLY"
    assert t381["submit_permission"] == "NO_SUBMIT"
    assert t381["testnet_submit_allowed"] is False
    assert t381["real_submit_allowed"] is False
    assert t381["submit_attempted"] is False
    assert t381["cancel_attempted"] is False
    assert t381["flatten_attempted"] is False
    for item in t381["queue_items"]:
        assert item["observation_only"] is True

    t382 = rules_v1.generate_shadow_data_quality_rules_v1(
        shadow_sample_quality_audit_json=str(reports / "shadow_sample_quality_audit" / "shadow_sample_quality_audit.json"),
        output_dir=str(reports / "shadow_data_quality_rules_v1"),
    )
    assert t382["task_id"] == "T382"
    assert t382["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t382["allowed_mode"] == "SHADOW_ONLY"
    assert t382["submit_permission"] == "NO_SUBMIT"
    assert t382["testnet_submit_allowed"] is False
    assert t382["real_submit_allowed"] is False
    assert t382["submit_attempted"] is False
    assert t382["cancel_attempted"] is False
    assert t382["flatten_attempted"] is False
    assert t382["timestamp_rules"]["allow_future_timestamp"] is False
    assert len(t382["required_fields"]) > 0
    assert len(t382["dedupe_key_fields"]) > 0

    t383 = blocker_map.map_readiness_blockers_to_actions(
        readiness_blocker_attribution_json=str(reports / "readiness_blocker_attribution" / "readiness_blocker_attribution.json"),
        shadow_only_backlog_prioritization_json=str(reports / "shadow_only_backlog_prioritization" / "shadow_only_backlog_prioritization.json"),
        output_dir=str(reports / "readiness_blocker_to_action_map_v1"),
    )
    assert t383["task_id"] == "T383"
    assert t383["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t383["allowed_mode"] == "SHADOW_ONLY"
    assert t383["submit_permission"] == "NO_SUBMIT"
    assert t383["testnet_submit_allowed"] is False
    assert t383["real_submit_allowed"] is False
    assert t383["submit_attempted"] is False
    assert t383["cancel_attempted"] is False
    assert t383["flatten_attempted"] is False
    for action in t383["actions"]:
        assert action["shadow_only"] is True
        assert action["priority"] != "CRITICAL" or action["category"] != "SAFETY"

    t384 = preflight_v1.generate_shadow_collection_preflight_v1(
        shadow_collection_queue_v1_json=str(reports / "shadow_collection_queue_v1" / "shadow_collection_queue_v1.json"),
        shadow_data_quality_rules_v1_json=str(reports / "shadow_data_quality_rules_v1" / "shadow_data_quality_rules_v1.json"),
        readiness_blocker_to_action_map_v1_json=str(reports / "readiness_blocker_to_action_map_v1" / "readiness_blocker_to_action_map_v1.json"),
        output_dir=str(reports / "shadow_collection_preflight_v1"),
    )
    assert t384["task_id"] == "T384"
    assert t384["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t384["allowed_mode"] == "SHADOW_ONLY"
    assert t384["submit_permission"] == "NO_SUBMIT"
    assert t384["testnet_submit_allowed"] is False
    assert t384["real_submit_allowed"] is False
    assert t384["submit_attempted"] is False
    assert t384["cancel_attempted"] is False
    assert t384["flatten_attempted"] is False
    assert "SHADOW_ONLY" in t384["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in t384["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in t384["allowed_actions"]

    t385 = phase_control_v5.generate_shadow_phase_control_report_v5(
        shadow_collection_preflight_v1_json=str(reports / "shadow_collection_preflight_v1" / "shadow_collection_preflight_v1.json"),
        testnet_dry_run_readiness_v4_json=str(reports / "testnet_dry_run_readiness_v4" / "testnet_dry_run_readiness_v4_report.json"),
        output_dir=str(reports / "shadow_phase_control_v5"),
    )
    assert t385["task_id"] == "T385"
    assert t385["final_verdict"] in ("PASS", "PARTIAL", "FAIL")
    assert t385["allowed_mode"] == "SHADOW_ONLY"
    assert t385["submit_permission"] == "NO_SUBMIT"
    assert t385["testnet_submit_allowed"] is False
    assert t385["real_submit_allowed"] is False
    assert t385["submit_attempted"] is False
    assert t385["cancel_attempted"] is False
    assert t385["flatten_attempted"] is False
    assert t385["final_decision"] in ("CONTINUE_SHADOW_ONLY", "READY_FOR_SHADOW_COLLECTION")
    assert t385["final_decision"] != "TESTNET_DRY_RUN_ONLY"
    assert t385["archive_range"] == "T208-T385"
    assert t385["next_recommended_task_range"] == "T386-T390"
    assert "SHADOW_ONLY" in t385["allowed_actions"]
    assert "TESTNET_DRY_RUN_BLOCKED" in t385["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in t385["allowed_actions"]


def test_t385_with_readiness_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    for folder in [
        "shadow_collection_preflight_v1",
        "testnet_dry_run_readiness_v4",
        "shadow_phase_control_v5",
    ]:
        (reports / folder).mkdir(parents=True, exist_ok=True)

    (reports / "shadow_collection_preflight_v1" / "shadow_collection_preflight_v1.json").write_text(
        json.dumps({
            "task_id": "T384",
            "preflight_ready": True,
            "queue_ready": True,
            "quality_gate_ready": True,
            "action_map_ready": True,
            "final_verdict": "PASS",
            "allowed_mode": "SHADOW_ONLY",
            "submit_permission": "NO_SUBMIT",
            "testnet_submit_allowed": False,
            "real_submit_allowed": False,
            "submit_attempted": False,
            "cancel_attempted": False,
            "flatten_attempted": False,
            "allowed_actions": ["SHADOW_ONLY", "TESTNET_DRY_RUN_BLOCKED"],
        }),
        encoding="utf-8",
    )
    (reports / "testnet_dry_run_readiness_v4" / "testnet_dry_run_readiness_v4_report.json").write_text(
        json.dumps({
            "task_id": "T374",
            "final_verdict": "NOT_READY",
            "allow_testnet_dry_run": False,
        }),
        encoding="utf-8",
    )

    t385 = phase_control_v5.generate_shadow_phase_control_report_v5(
        shadow_collection_preflight_v1_json=str(reports / "shadow_collection_preflight_v1" / "shadow_collection_preflight_v1.json"),
        testnet_dry_run_readiness_v4_json=str(reports / "testnet_dry_run_readiness_v4" / "testnet_dry_run_readiness_v4_report.json"),
        output_dir=str(reports / "shadow_phase_control_v5"),
    )

    assert t385["readiness_status"] == "NOT_READY"
    assert t385["final_decision"] in ("CONTINUE_SHADOW_ONLY", "READY_FOR_SHADOW_COLLECTION")
    assert "TESTNET_DRY_RUN_BLOCKED" in t385["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" not in t385["allowed_actions"]
    assert t385["testnet_submit_allowed"] is False
    assert t385["real_submit_allowed"] is False


def test_scripts_support_json_flag() -> None:
    p1 = queue_v1.build_arg_parser()
    p2 = rules_v1.build_arg_parser()
    p3 = blocker_map.build_arg_parser()
    p4 = preflight_v1.build_arg_parser()
    p5 = phase_control_v5.build_arg_parser()

    a1 = [a.dest for a in p1._actions]
    a2 = [a.dest for a in p2._actions]
    a3 = [a.dest for a in p3._actions]
    a4 = [a.dest for a in p4._actions]
    a5 = [a.dest for a in p5._actions]

    assert "json" in a1
    assert "json" in a2
    assert "json" in a3
    assert "json" in a4
    assert "json" in a5
