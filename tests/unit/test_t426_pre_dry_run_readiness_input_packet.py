import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_pre_dry_run_readiness_input_packet_v1 import (
    load_json,
    write_json,
    build_packet,
    main
)


def test_ready_case(tmp_path):
    gap_report = {
        "readiness_status": "GAP_VALIDATED_PENDING_REVIEW",
        "final_decision": "READY_FOR_MANUAL_REVIEW_AFTER_GAP_VALIDATION"
    }
    manual_report = {
        "manual_review_phase_completed": True,
        "phase_completion_status": "COMPLETED_PENDING_PRE_DRY_RUN_REVIEW"
    }
    gap_path = str(tmp_path / "gap.json")
    manual_path = str(tmp_path / "manual.json")
    write_json(gap_path, gap_report)
    write_json(manual_path, manual_report)

    packet = build_packet(gap_report, manual_report, gap_path, manual_path)

    assert packet["ok"] is True
    assert packet["input_status"] == "READY_FOR_PRE_DRY_RUN_READINESS_REVIEW"
    assert packet["final_decision"] == "READY_FOR_MANUAL_PRE_DRY_RUN_REVIEW_INPUT_PACKET"


def test_gap_blocked(tmp_path):
    gap_report = {"readiness_status": "NOT_READY", "final_decision": "CONTINUE_SHADOW_COLLECTION"}
    manual_report = {"manual_review_phase_completed": True}
    gap_path = str(tmp_path / "gap.json")
    manual_path = str(tmp_path / "manual.json")
    write_json(gap_path, gap_report)
    write_json(manual_path, manual_report)

    packet = build_packet(gap_report, manual_report, gap_path, manual_path)

    assert packet["input_status"] == "BLOCKED_BY_GAP_VALIDATION"
    assert packet["final_decision"] == "CONTINUE_SHADOW_COLLECTION"


def test_manual_blocked(tmp_path):
    gap_report = {"readiness_status": "GAP_VALIDATED_PENDING_REVIEW"}
    manual_report = {"manual_review_phase_completed": False}
    gap_path = str(tmp_path / "gap.json")
    manual_path = str(tmp_path / "manual.json")
    write_json(gap_path, gap_report)
    write_json(manual_path, manual_report)

    packet = build_packet(gap_report, manual_report, gap_path, manual_path)

    assert packet["input_status"] == "BLOCKED_BY_MANUAL_REVIEW_PHASE"
    assert packet["final_decision"] == "CONTINUE_MANUAL_REVIEW"


def test_both_blocked(tmp_path):
    gap_report = {"readiness_status": "NOT_READY"}
    manual_report = {"manual_review_phase_completed": False}
    gap_path = str(tmp_path / "gap.json")
    manual_path = str(tmp_path / "manual.json")
    write_json(gap_path, gap_report)
    write_json(manual_path, manual_report)

    packet = build_packet(gap_report, manual_report, gap_path, manual_path)

    assert packet["input_status"] == "BLOCKED_BY_GAP_AND_MANUAL_REVIEW"
    assert packet["final_decision"] == "CONTINUE_SHADOW_COLLECTION"


def test_safety_invariants(tmp_path):
    packet = build_packet(None, None, "gap.json", "manual.json")

    assert packet["safety_flags"]["testnet_dry_run_allowed"] is False
    assert packet["safety_flags"]["testnet_submit_allowed"] is False
    assert packet["safety_flags"]["real_submit_allowed"] is False
    assert packet["safety_flags"]["submit_attempted"] is False
    assert packet["safety_flags"]["cancel_attempted"] is False
    assert packet["safety_flags"]["flatten_attempted"] is False
    assert "TESTNET_DRY_RUN_ONLY" not in packet["allowed_actions"]
    assert "TESTNET_SUBMIT" not in packet["allowed_actions"]
    assert "TESTNET_DRY_RUN_ONLY" in packet["blocked_actions"]
    assert "TESTNET_SUBMIT" in packet["blocked_actions"]


def test_invalid_json(tmp_path):
    gap_path = str(tmp_path / "gap.json")
    manual_path = str(tmp_path / "manual.json")
    with open(gap_path, "w") as f:
        f.write("not valid json")
    with open(manual_path, "w") as f:
        json.dump({"manual_review_phase_completed": True}, f)

    packet = build_packet(load_json(gap_path), load_json(manual_path), gap_path, manual_path)

    assert packet["ok"] is False


def test_missing_file(tmp_path):
    gap_path = str(tmp_path / "gap.json")
    manual_path = str(tmp_path / "manual.json")

    packet = build_packet(load_json(gap_path), load_json(manual_path), gap_path, manual_path)

    assert packet["ok"] is False


def test_cli_smoke(tmp_path):
    gap_report = {"readiness_status": "GAP_VALIDATED_PENDING_REVIEW"}
    manual_report = {"manual_review_phase_completed": True}
    gap_path = str(tmp_path / "gap.json")
    manual_path = str(tmp_path / "manual.json")
    output_path = str(tmp_path / "output.json")
    write_json(gap_path, gap_report)
    write_json(manual_path, manual_report)

    proc = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).parent.parent.parent / "scripts" / "generate_pre_dry_run_readiness_input_packet_v1.py"),
            "--gap-control-report", gap_path,
            "--manual-review-phase-report", manual_path,
            "--output", output_path,
            "--json"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()

    assert proc.returncode in [0, 1]
    assert os.path.exists(output_path)
